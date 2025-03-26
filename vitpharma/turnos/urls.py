from django.urls import path
from . import views

app_name = 'turnos'

urlpatterns = [
    # Panel principal del módulo de turnos
    path('', views.turno_dashboard, name='turno_dashboard'),
    
]