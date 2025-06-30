import os, base64, re, html
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from django.http import JsonResponse
from google_auth_oauthlib.flow import Flow
from django.shortcuts import redirect
from django.conf import settings
from .email_cache import chroma_collection_name

load_dotenv()


# Utility: decode base64 Gmail message parts
def extract_text_from_payload(payload):
    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return ""


CHROMA_DB_DIR = "./chroma_db"  # Path must match your previous write location


def build_email_qa_chain_from_chroma(user_id: str):
    embeddings = OpenAIEmbeddings()

    vectorstore = Chroma(
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_DIR,
        collection_name=chroma_collection_name(user_id),
    )

    retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": 5})

    qa_chain = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(model="gpt-3.5-turbo", temperature=0),
        retriever=retriever,
        chain_type="map_reduce",  # ✅ avoids stuffing too many tokens
        return_source_documents=True,  # Optional: helpful for debugging
    )

    return qa_chain


# Step 1: Get and clean email content
def get_emails_from_gmail(session_credentials):
    creds = Credentials(**session_credentials)
    service = build("gmail", "v1", credentials=creds)

    results = (
        service.users()
        .messages()
        .list(userId="me", maxResults=100, q="category:primary")
        .execute()
    )
    message_ids = results.get("messages", [])

    emails = []
    for msg in message_ids:
        msg_data = service.users().messages().get(userId="me", id=msg["id"]).execute()
        payload = msg_data.get("payload", {})
        body = extract_text_from_payload(payload) or msg_data.get("snippet", "")
        cleaned = html.unescape(re.sub(r"[\u034f\u200c\ufeff]+", "", body)).strip()
        if cleaned:
            emails.append(cleaned)
    return emails


# Step 2: Build RAG chain
def build_email_qa_chain(emails):
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma.from_texts(emails, embedding=embeddings)
    qa_chain = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(model="gpt-3.5-turbo"), retriever=vectorstore.as_retriever()
    )
    return qa_chain


def oauth2callback(request):
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "redirect_uris": [settings.REDIRECT_URI],  # ✅ use from settings
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        redirect_uri=settings.REDIRECT_URI,  # ✅ use from settings
    )

    flow.fetch_token(authorization_response=request.build_absolute_uri())
    credentials = flow.credentials
    request.session["credentials"] = credentials_to_dict(credentials)

    return redirect("/email/ask")  # Or your frontend path


def email_assistant_view(request):
    creds = request.session.get("credentials")
    print(f"{request}")
    if not creds:
        return JsonResponse({"error": "Not authenticated"}, status=401)
    # ... fetch emails and answer question ...


def credentials_to_dict(credentials):
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }
