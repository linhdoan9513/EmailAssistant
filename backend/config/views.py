import logging
from django.http import JsonResponse, HttpRequest
from rest_framework.views import APIView
from rest_framework.response import Response
from .email_assistant import build_email_qa_chain_from_chroma
from django.conf import settings
from django.shortcuts import redirect

# # Set up logger
# logger = logging.getLogger(__name__)

def oauth2callback(request):
    return redirect(settings.FRONTEND_REDIRECT_URL)


class EmailAssistantView(APIView):
    def post(self, request):
        question = request.data.get("question")

        if not question:
            return Response({"error": "Please provide a question."}, status=400)

        creds = request.session.get("credentials")
        if not creds:
            return Response({"error": "Not authenticated with Gmail."}, status=401)

        try:
            # emails = get_emails_from_gmail(creds)
            qa_chain = build_email_qa_chain_from_chroma()
            
            answer_obj = qa_chain.invoke({"query": question})

            answer = answer_obj["result"] if isinstance(answer_obj, dict) and "result" in answer_obj else answer_obj
            return Response({"answer": answer})
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def get(self, request):
        return Response({"message": "POST a JSON body with a 'question' field."})


def user_profile(request):
    creds = request.session.get("credentials")
    if not creds:
        return JsonResponse({"error": "Not authenticated"}, status=401)

    email = request.session.get("user_email")
    if not email:
        return JsonResponse({"error": "Email not found"}, status=404)

    return JsonResponse({"email": email})


def gmail_logout(request):
    request.session.flush()
    return JsonResponse({"message": "Logged out successfully."})
