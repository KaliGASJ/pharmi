from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    # Vista principal del módulo de ventas (registro)
    path('registrar/', views.venta_dashboard, name='venta_dashboard'),
    
    # Cancelar una venta en proceso
    path('cancelar/', views.cancelar_venta, name='cancelar_venta'),
    
    # Ver historial de ventas del usuario actual
    path('historial/', views.historial_ventas, name='historial_ventas'),
    
    # Ver detalle específico de una venta
    path('detalle/<int:venta_id>/', views.detalle_venta, name='detalle_venta'),
    
    # Descargar ticket de una venta activa en PDF
    path('venta/<int:venta_id>/ticket/', views.generar_ticket_pdf, name='generar_ticket_pdf'),
    
    # Cancelar una venta ya registrada
    path('venta/<int:venta_id>/cancelar/', views.cancelar_venta_existente, name='cancelar_venta_existente'),
    
    # AJAX para obtener lotes de un producto
    path('get-lotes-producto/', views.get_lotes_producto, name='get_lotes_producto'),
    
    # AJAX para obtener información detallada de un lote
    path('get-info-lote/', views.get_info_lote, name='get_info_lote'),
    
    # AJAX para agregar un producto al carrito
    path('agregar-al-carrito/', views.agregar_al_carrito, name='agregar_al_carrito'),
]