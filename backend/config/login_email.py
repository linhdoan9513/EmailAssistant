from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from django.shortcuts import redirect
from django.http import JsonResponse
import os
from dotenv import load_dotenv
load_dotenv()

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

    # ✅ Get both auth_url and state explicitly
    auth_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true'
    )

    request.session['google_auth_state'] = state  # ✅ this now works
    return redirect(auth_url)


# Step 2: Handle Google redirect
def oauth2callback(request):
    state = request.session.get('google_auth_state')

    if not state:
        return JsonResponse({"error": "Missing OAuth state in session"}, status=400)

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
        state=state,
        redirect_uri=REDIRECT_URI
    )

    flow.fetch_token(authorization_response=request.build_absolute_uri())
    credentials = flow.credentials

    # Store credentials in session for now
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
