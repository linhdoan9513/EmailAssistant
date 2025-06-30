import os
from dotenv import load_dotenv
from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


# Step 1: Redirect to Google login
def gmail_login(request):
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [settings.REDIRECT_URI],  # ✅ Use from settings
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.REDIRECT_URI,  # ✅ Use from settings
    )

    auth_url, state = flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true"
    )

    request.session["google_auth_state"] = state
    return redirect(auth_url)


def oauth2callback(request):
    state = request.session.get("google_auth_state")
    if not state:
        return JsonResponse({"error": "Missing OAuth state in session"}, status=400)

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [settings.REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        state=state,
        redirect_uri=settings.REDIRECT_URI,
    )

    flow.fetch_token(authorization_response=request.build_absolute_uri())
    credentials = flow.credentials

    # Fetch user email
    service = build("gmail", "v1", credentials=credentials)
    profile = service.users().getProfile(userId="me").execute()
    user_email = profile["emailAddress"]

    # 🔐 Create or get Django user based on Gmail address
    user, created = User.objects.get_or_create(
        username=user_email, defaults={"email": user_email}
    )

    # 🔐 Log them into Django session
    login(request, user)

    # ✅ Store Gmail credentials tied to the logged-in user
    user_id = str(user.id)
    credentials_by_user = request.session.get("credentials_by_user", {})
    credentials_by_user[user_id] = credentials_to_dict(credentials)
    request.session["credentials_by_user"] = credentials_by_user
    request.session["user_email"] = user_email
    request.session.modified = True

    # ✅ Redirect to frontend
    return redirect(settings.FRONTEND_REDIRECT_URL)


def credentials_to_dict(credentials):
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }
