from django.urls import path
from . import views

app_name = 'consultas'

urlpatterns = [
    path('', views.consultas_vendedor, name='consultas_vendedor'),
]
