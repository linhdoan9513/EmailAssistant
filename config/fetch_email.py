import os
import re
import html
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.http import JsonResponse
from django.utils.html import escape
from collections import defaultdict

from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from .email_cache import load_processed_ids, save_processed_ids, chroma_collection_name
import traceback

# from django.contrib.auth.decorators import login_required

CHROMA_DIR = "./chroma_db"


def clean_text(text):
    text = html.unescape(text)
    text = re.sub(r"[\u034f\u200c\ufeff]+", "", text)
    return text.strip()


def extract_email_body(payload):
    """Recursively extract plain text from the email payload."""
    if payload.get("mimeType") == "text/plain":
        body_data = payload.get("body", {}).get("data")
        if body_data:
            return clean_text(
                base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
            )
    elif payload.get("mimeType", "").startswith("multipart/"):
        parts = payload.get("parts", [])
        for part in parts:
            result = extract_email_body(part)
            if result:
                return result
    return ""


def get_credentials(request):
    user_id = str(request.user.id)
    credentials_by_user = request.session.get("credentials_by_user")

    if not credentials_by_user:
        return None

    credentials_data = credentials_by_user.get(user_id)
    return Credentials(**credentials_data) if credentials_data else None


def get_message_ids(service, max_results=100, query="category:primary"):
    results = (
        service.users()
        .messages()
        .list(userId="me", maxResults=max_results, q=query)
        .execute()
    )
    return results.get("messages", [])


def build_documents_from_messages(service, message_ids):
    documents = []

    for msg in message_ids:
        msg_data = (
            service.users()
            .messages()
            .get(userId="me", id=msg["id"], format="full")
            .execute()
        )

        payload = msg_data.get("payload", {})
        body = extract_email_body(payload)
        if not body:
            continue

        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
        subject = headers.get("Subject", "")
        sender = headers.get("From", "")
        thread_id = msg_data.get("threadId", "")

        combined_content = f"From: {sender}\nSubject: {subject}\n\n{body}"
        documents.append(
            Document(
                page_content=combined_content,
                metadata={"subject": subject, "from": sender, "thread_id": thread_id},
            )
        )

    return documents


def store_documents_in_vector_db(documents, user_id: str):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    split_docs = splitter.split_documents(documents)

    Chroma.from_documents(
        documents=split_docs,
        embedding=OpenAIEmbeddings(),
        persist_directory=CHROMA_DIR,
        collection_name=chroma_collection_name(user_id),
    ).persist()


def group_documents_by_thread(documents):
    thread_map = defaultdict(list)

    for doc in documents:
        metadata = doc.metadata or {}

        thread_id = metadata.get("thread_id")
        if not thread_id:
            continue  # Skip if missing thread_id

        thread_map[thread_id].append(
            {
                "subject": metadata.get("subject", ""),
                "from": metadata.get("from", ""),
                "snippet": escape(doc.page_content[:300]).replace("\n", "<br>"),
                "full_body": escape(doc.page_content).replace("\n", "<br>"),
            }
        )

    return [
        {"thread_id": thread_id, "emails": sorted(emails, key=lambda x: x["subject"])}
        for thread_id, emails in thread_map.items()
    ]


def load_existing_threads_from_chroma(user_id: str):
    vectorstore = Chroma(
        embedding_function=OpenAIEmbeddings(),
        persist_directory=CHROMA_DIR,
        collection_name=chroma_collection_name(user_id),
    )
    docs = vectorstore.similarity_search("inbox", k=200)  # dummy query
    threads = group_documents_by_thread(docs)
    return JsonResponse(
        {
            "stored": 0,
            "collection": chroma_collection_name(user_id),
            "vector_db_path": os.path.abspath(CHROMA_DIR),
            "threads": threads,
        }
    )


def load_gmail_threads_to_chroma(request):
    try:
        # # 1️⃣  Make sure the caller is logged in to **your** app
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Unauthenticated"}, status=401)

        user_id = str(request.user.id)

        # 2️⃣  Pull the Gmail OAuth token tied to this user
        creds = get_credentials(request)
        if not creds:
            return JsonResponse({"error": "No Gmail credentials found"}, status=401)

        # 3️⃣  Build the Gmail service
        gmail_service = build("gmail", "v1", credentials=creds)

        # profile = gmail_service.users().getProfile(userId="me").execute()

        # 4️⃣  Fetch message IDs from Primary tab
        all_message_ids = get_message_ids(gmail_service)  # <- unchanged helper
        if not all_message_ids:
            return load_existing_threads_from_chroma(user_id)  # <- unchanged helper

        # 5️⃣  Deduplicate against the local cache
        cached_ids = load_processed_ids(user_id)
        new_message_ids = [
            msg for msg in all_message_ids if msg["id"] not in cached_ids
        ]

        if new_message_ids:
            documents = build_documents_from_messages(  # <- unchanged helper
                gmail_service, new_message_ids
            )
            if not documents:
                return JsonResponse({"message": "No valid content to embed."})

            store_documents_in_vector_db(documents, user_id)  # <- unchanged helper
            save_processed_ids(
                user_id, cached_ids.union({msg["id"] for msg in new_message_ids})
            )
            threads = group_documents_by_thread(documents)  # <- unchanged helper

            return JsonResponse(
                {
                    "stored": len(documents),
                    "collection": "gmail_emails",
                    "vector_db_path": os.path.abspath(CHROMA_DIR),
                    "threads": threads,
                }
            )
        return load_existing_threads_from_chroma(user_id)  # <- unchanged helper

    except Exception:
        traceback.print_exc()
        return JsonResponse(
            {"error": "Internal server error while syncing Gmail"},
            status=500,
        )
