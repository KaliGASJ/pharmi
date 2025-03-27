from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    # Vista principal del registro de ventas
    path('registrar/', views.venta_dashboard, name='venta_dashboard'),

    # API: Buscar productos + lotes disponibles (usado por el nuevo carrito dinámico)
    path('api/buscar/', views.api_buscar_productos, name='api_buscar_productos'),

    # Procesar la venta
    path('procesar/', views.procesar_venta, name='procesar_venta'),

    # Ver detalle de una venta
    path('detalle/<int:venta_id>/', views.detalle_venta, name='detalle_venta'),

    # Historial de ventas del vendedor
    path('historial/', views.historial_ventas, name='historial_ventas'),

    # Cancelar una venta específica
    path('cancelar/<int:venta_id>/', views.cancelar_venta, name='cancelar_venta'),

    # Generar y mostrar el PDF del ticket de venta
    path('ticket/<int:venta_id>/', views.generar_ticket_pdf, name='generar_ticket_pdf'),

    # API JSON para obtener ventas recientes
    path('api/json/', views.ventas_api_json, name='ventas_api_json'),

    # Filtro de ventas por fechas
    path('filtro/', views.ventas_por_fecha, name='ventas_por_fecha'),
]
