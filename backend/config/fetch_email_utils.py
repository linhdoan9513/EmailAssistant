import os
import re
import html
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.http import JsonResponse

from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.schema import Document

CHROMA_DIR = "./chroma_db"

def clean_text(text):
    text = html.unescape(text)
    text = re.sub(r'[\u034f\u200c\ufeff]+', '', text)
    return text.strip()

def extract_email_body(payload):
    """Recursively extract plain text from the email payload."""
    if payload.get("mimeType") == "text/plain":
        body_data = payload.get("body", {}).get("data")
        if body_data:
            return clean_text(base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore"))
    elif payload.get("mimeType", "").startswith("multipart/"):
        parts = payload.get("parts", [])
        for part in parts:
            result = extract_email_body(part)
            if result:
                return result
    return ""

def fetch_gmail_messages(request):
    credentials_data = request.session.get("credentials")
    if not credentials_data:
        return JsonResponse({"error": "No credentials found"}, status=401)

    creds = Credentials(**credentials_data)
    service = build('gmail', 'v1', credentials=creds)

    results = service.users().messages().list(
        userId='me',
        maxResults=100,
        q="category:primary"
    ).execute()

    message_ids = results.get('messages', [])
    if not message_ids:
        return JsonResponse({"message": "No emails found."})

    documents = []

    for msg in message_ids:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        payload = msg_data.get("payload", {})
        body = extract_email_body(payload)
        if not body:
            continue

        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
        subject = headers.get("Subject", "")
        sender = headers.get("From", "")

        documents.append(Document(
            page_content=body,
            metadata={"subject": subject, "from": sender}
        ))

    if not documents:
        return JsonResponse({"message": "No valid content to embed."})

    vectorstore = Chroma.from_documents(
        documents,
        embedding=OpenAIEmbeddings(),
        persist_directory=CHROMA_DIR,
        collection_name="gmail_emails"
    )
    vectorstore.persist()

    return JsonResponse({
        "stored": len(documents),
        "collection": "gmail_emails",
        "vector_db_path": os.path.abspath(CHROMA_DIR),
        "emails": [doc.metadata for doc in documents]
    })
