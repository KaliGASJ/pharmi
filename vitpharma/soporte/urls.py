from django.urls import path
from . import views

app_name = 'soporte'

urlpatterns = [
    path('chat/', views.chatbot_view, name='chatbot_view'),
]
