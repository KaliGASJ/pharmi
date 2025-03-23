from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    path('registrar/', views.registro_venta, name='registro_venta'),
]
