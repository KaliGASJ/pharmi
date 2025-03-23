from django.urls import path
from . import views

app_name = 'turnos'

urlpatterns = [
    path('', views.turno_vendedor, name='turno_vendedor'),
     path('finalizar/', views.finalizar_turno, name='finalizar_turno'),  # ← esta es la nueva
]