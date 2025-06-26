import logging
from django.http import JsonResponse, HttpRequest
from rest_framework.views import APIView
from rest_framework.response import Response
from .email_assistant import get_emails_from_gmail, build_email_qa_chain
from django.conf import settings
from django.shortcuts import redirect

# Set up logger
logger = logging.getLogger(__name__)

def oauth2callback(request):
    return redirect(settings.FRONTEND_REDIRECT_URL)


class EmailAssistantView(APIView):
    def post(self, request):
        logger.info("📥 Received POST /email/ask/")
        question = request.data.get("question")
        logger.debug(f"🔍 Question received: {question}")

        if not question:
            logger.warning("⚠️ No question provided")
            return Response({"error": "Please provide a question."}, status=400)

        creds = request.session.get("credentials")
        if not creds:
            logger.warning("❌ No credentials in session")
            return Response({"error": "Not authenticated with Gmail."}, status=401)

        try:
            logger.info("✅ Credentials found. Fetching emails...")
            emails = get_emails_from_gmail(creds)

            logger.info(f"📨 Fetched {len(emails)} emails")
            qa_chain = build_email_qa_chain(emails)

            logger.info("🧠 Running QA chain...")
            answer_obj = qa_chain.invoke({"query": question})
            logger.debug(f"🧪 Raw QA result: {answer_obj}")

            answer = answer_obj["result"] if isinstance(answer_obj, dict) and "result" in answer_obj else answer_obj
            logger.info("✅ Successfully generated answer")
            return Response({"answer": answer})
        except Exception as e:
            logger.exception("💥 Error in EmailAssistantView POST")
            return Response({"error": str(e)}, status=500)

    def get(self, request):
        logger.info("📤 Received GET /email/ask/")
        return Response({"message": "POST a JSON body with a 'question' field."})


def user_profile(request):
    logger.info("🔍 Checking user profile")
    creds = request.session.get("credentials")
    if not creds:
        logger.warning("❌ Not authenticated for user profile")
        return JsonResponse({"error": "Not authenticated"}, status=401)

    email = request.session.get("user_email")
    if not email:
        logger.warning("❌ Email not found in session")
        return JsonResponse({"error": "Email not found"}, status=404)

    logger.info(f"✅ Found user email: {email}")
    return JsonResponse({"email": email})


def gmail_logout(request):
    logger.info("🚪 Logging out user...")
    request.session.flush()
    return JsonResponse({"message": "Logged out successfully."})
