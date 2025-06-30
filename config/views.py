import logging
from django.http import JsonResponse, HttpRequest
from rest_framework.views import APIView
from rest_framework.response import Response
from .email_assistant import build_email_qa_chain_from_chroma
from django.conf import settings
from django.shortcuts import redirect
from google.oauth2.credentials import Credentials

# # Set up logger
# logger = logging.getLogger(__name__)


def oauth2callback(request):
    return redirect(settings.FRONTEND_REDIRECT_URL)


def get_credentials(request):
    user_id = str(request.user.id)
    credentials_by_user = request.session.get("credentials_by_user")

    if not credentials_by_user:
        return None

    credentials_data = credentials_by_user.get(user_id)
    return Credentials(**credentials_data) if credentials_data else None


class EmailAssistantView(APIView):
    def post(self, request):
        print(f"🤩 running line 31")
        question = request.data.get("question")

        if not question:
            return Response({"error": "Please provide a question."}, status=400)

            # # 1️⃣  Make sure the caller is logged in to **your** app
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Unauthenticated"}, status=401)

        user_id = str(request.user.id)

        # 2️⃣  Pull the Gmail OAuth token tied to this user
        creds = get_credentials(request)
        if not creds:
            return JsonResponse({"error": "No Gmail credentials found"}, status=401)

        try:
            qa_chain = build_email_qa_chain_from_chroma()
            answer_obj = qa_chain.invoke({"query": question})
            # ✅ Extract answer + retrieved documents
            if isinstance(answer_obj, dict):
                answer = (
                    answer_obj.get("result") or answer_obj.get("answer") or "No answer."
                )
                source_docs = answer_obj.get("source_documents", [])
            else:
                print(f"runnign line 58")
                answer = answer_obj
                source_docs = []

            # ✅ Optional: Print to console for debugging
            print("\n🔍 Retrieved Documents:")
            print(f"\n🔍 Source: ${source_docs}")
            for i, doc in enumerate(source_docs):
                print(
                    f"[{i+1}] {doc.metadata.get('subject', 'No Subject')} - {doc.metadata.get('from', '')}"
                )
                print(doc.page_content[:300])
                print("---")

            return Response(
                {
                    "answer": answer,
                    "sources": [
                        {
                            "subject": doc.metadata.get("subject", ""),
                            "from": doc.metadata.get("from", ""),
                            "preview": doc.page_content[:300],
                        }
                        for doc in source_docs
                    ],
                }
            )
            # answer = (
            #     answer_obj["result"]
            #     if isinstance(answer_obj, dict) and "result" in answer_obj
            #     else answer_obj
            # )
            # return Response({"answer": answer})
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def get(self, request):
        return Response({"message": "POST a JSON body with a 'question' field."})


def user_profile(request):
    # ✅ Check if Django user is logged in
    if not request.user.is_authenticated:
        return JsonResponse({"error": "User not logged in"}, status=401)

    # ✅ Now you can safely pull Gmail email
    email = request.session.get("user_email")
    if not email:
        return JsonResponse({"error": "Email not found"}, status=404)

    return JsonResponse({"email": email})


def gmail_logout(request):
    request.session.flush()
    return JsonResponse({"message": "Logged out successfully."})
