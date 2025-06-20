
from django.http import JsonResponse
from django.http import HttpRequest

def oauth2callback(request):
    return JsonResponse({"message": "OAuth callback reached!"})
 