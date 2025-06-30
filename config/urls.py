"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from .login_email import gmail_login, oauth2callback
from .fetch_email import load_gmail_threads_to_chroma
from .views import EmailAssistantView, user_profile
from django.http import HttpResponse
from .views import EmailAssistantView, user_profile, gmail_logout


def home(request):
    return HttpResponse("Welcome to Email Assistant!")


urlpatterns = [
    path("", home),  # Add this line for the root path
    path("admin/", admin.site.urls),
    path("gmail/login/", gmail_login, name="gmail_login"),
    path("oauth2callback/", oauth2callback, name="oauth2callback"),
    path("gmail/fetch/", load_gmail_threads_to_chroma, name="fetch_gmail"),
    path("email/ask/", EmailAssistantView.as_view(), name="email_assistant"),
    path("user/profile/", user_profile, name="user_profile"),
    path("gmail/logout/", gmail_logout, name="gmail_logout"),
]
