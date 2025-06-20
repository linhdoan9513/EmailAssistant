import re
import html
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.http import JsonResponse

def clean_snippet(text):
    # Decode HTML entities
    text = html.unescape(text)
    # Remove invisible Unicode characters
    text = re.sub(r'[\u034f\u200c\ufeff]+', '', text)
    return text.strip()

def fetch_gmail_messages(request):
    credentials_data = request.session.get("credentials")

    if not credentials_data:
        return JsonResponse({"error": "No credentials found"}, status=401)

    creds = Credentials(**credentials_data)
    service = build('gmail', 'v1', credentials=creds)

    # ✅ Only fetch messages from Primary category
    results = service.users().messages().list(
        userId='me',
        maxResults=100,
        q="category:primary"
    ).execute()

    message_ids = results.get('messages', [])
    emails = []

    for msg in message_ids:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        snippet = msg_data.get("snippet", "")
        emails.append(clean_snippet(snippet))

    return JsonResponse({"emails": emails})
