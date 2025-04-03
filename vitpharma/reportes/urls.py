from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    # DASHBOARD VISUAL DE REPORTES
    path('dashboard/', views.dashboard_reportes, name='dashboard_reportes'),
    
    # VISTAS HTML
    path('cajas-general/', views.reporte_cajas_general, name='reporte_cajas_general'),
    path('cortes-admin/', views.historial_cortes_admin, name='historial_cortes_admin'),
    path('ventas-admin/', views.historial_ventas_admin, name='historial_ventas_admin'),
    path('inventario-admin/', views.reporte_inventario_admin, name='reporte_inventario_admin'),
    path('proveedores/', views.reporte_proveedores, name='reporte_proveedores'),

    # EXPORTACIONES PDF
    path('cajas-general/pdf/', views.exportar_reporte_cajas_pdf, name='exportar_reporte_cajas_pdf'),
    path('cortes-admin/pdf/', views.exportar_cortes_admin_pdf, name='exportar_cortes_admin_pdf'),
    path('ventas-admin/pdf/', views.exportar_historial_ventas_pdf, name='exportar_historial_ventas_pdf'),
    path('inventario-admin/pdf/', views.exportar_inventario_pdf, name='exportar_inventario_pdf'),
    path('proveedores/pdf/', views.exportar_proveedores_pdf, name='exportar_proveedores_pdf'),
]
