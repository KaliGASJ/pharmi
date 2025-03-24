from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    # Vista principal para registrar ventas
    path('registrar/', views.registro_venta, name='registro_venta'),
    
    # API para búsqueda de productos en tiempo real
    path('buscar-productos/', views.buscar_productos, name='buscar_productos'),
    
    # Procesamiento de ventas
    path('procesar-venta/', views.procesar_venta, name='procesar_venta'),
    
    # Historial de ventas
    path('historial/', views.historial_ventas, name='historial_ventas'),
    
    # Detalle de una venta específica
    path('detalle/<int:venta_id>/', views.detalle_venta, name='detalle_venta'),
    
    # Descarga de ticket
    path('ticket/<int:venta_id>/', views.descargar_ticket, name='descargar_ticket'),
    
    # Gestión de métodos de pago
    path('metodos-pago/', views.metodos_pago, name='metodos_pago'),
    
    # Cancelación de venta (funcionalidad futura)
    path('cancelar/<int:venta_id>/', views.cancelar_venta, name='cancelar_venta'),
]