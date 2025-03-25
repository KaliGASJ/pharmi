from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    # Registro y procesamiento de ventas
    path('registrar/', views.venta_dashboard, name='venta_dashboard'),
]
