from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    # Vista principal del módulo de ventas (registro)
    path('registrar/', views.venta_dashboard, name='venta_dashboard'),
]