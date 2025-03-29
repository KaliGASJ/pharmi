from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    # Vista principal del registro de ventas
    path('registrar/', views.venta_dashboard, name='venta_dashboard'),

    # API: Buscar productos (por nombre o código de barras)
    path('api/buscar/', views.api_buscar_productos, name='api_buscar_productos'),

    # API: Cargar lotes del producto seleccionado
    path('api/lotes/<int:producto_id>/', views.api_lotes_por_producto, name='api_lotes_por_producto'),

    # Procesar venta
    path('procesar/', views.procesar_venta, name='procesar_venta'),

    # Detalle de una venta
    path('detalle/<int:venta_id>/', views.detalle_venta, name='detalle_venta'),

    # Historial de ventas del vendedor
    path('historial/', views.historial_ventas, name='historial_ventas'),

    # Cancelar venta
    path('cancelar/<int:venta_id>/', views.cancelar_venta, name='cancelar_venta'),

    # Generar y visualizar PDF del ticket
    path('ticket/<int:venta_id>/', views.generar_ticket_pdf, name='generar_ticket_pdf'),

    # API JSON: últimas ventas del usuario
    path('api/json/', views.ventas_api_json, name='ventas_api_json'),

    # Filtro de ventas por fecha
    path('filtro/', views.ventas_por_fecha, name='ventas_por_fecha'),
]
