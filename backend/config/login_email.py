from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from django.shortcuts import redirect
from django.conf import settings
import os, pathlib
from django.http import JsonResponse

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
REDIRECT_URI = 'http://localhost:8000/oauth2callback/'

# Step 1: Redirect to Google login
def gmail_login(request):
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    request.session['flow'] = flow.credentials_to_dict()
    return redirect(auth_url)

# Step 2: Handle Google redirect
def oauth2callback(request):
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    credentials = flow.credentials
    request.session['credentials'] = credentials_to_dict(credentials)
    return JsonResponse({"message": "Successfully authenticated with Gmail!"})

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
