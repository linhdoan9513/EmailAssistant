
from django.http import JsonResponse
from django.http import HttpRequest
from rest_framework.views import APIView
from rest_framework.response import Response
from .email_assistant import get_emails_from_gmail, build_email_qa_chain

def oauth2callback(request):
    return JsonResponse({"message": "OAuth callback reached!"})


class EmailAssistantView(APIView):
    def post(self, request):
        question = request.data.get("question")
        if not question:
            return Response({"error": "Please provide a question."}, status=400)

        creds = request.session.get("credentials")
        if not creds:
            return Response({"error": "Not authenticated with Gmail."}, status=401)

        try:
            emails = get_emails_from_gmail(creds)
            qa_chain = build_email_qa_chain(emails)
            answer = qa_chain.run(question)
            return Response({"answer": answer})
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def get(self, request):
        return Response({"message": "POST a JSON body with a 'question' field."})