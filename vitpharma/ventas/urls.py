from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    # Vista principal del módulo de ventas (registro)
    path('registrar/', views.venta_dashboard, name='venta_dashboard'),

    # Cancelar una venta
    path('cancelar/', views.cancelar_venta, name='cancelar_venta'),

    # Ver historial de ventas del usuario actual
    path('historial/', views.historial_ventas, name='historial_ventas'),

    # Ver detalle específico de una venta
    path('detalle/<int:venta_id>/', views.detalle_venta, name='detalle_venta'),

    # Descargar ticket de una venta activa en PDF
    path('venta/<int:venta_id>/ticket/', views.generar_ticket_pdf, name='generar_ticket_pdf'),
]
