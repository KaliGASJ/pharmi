from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    # Listado de productos
    path("productos/", views.listar_productos, name="listar_productos"),

    # Administrador: Gestión de productos
    path("productos/agregar/", views.agregar_producto, name="agregar_producto"),
    path("productos/editar/<int:producto_id>/", views.editar_producto, name="editar_producto"),
    path("productos/eliminar/<int:producto_id>/", views.eliminar_producto, name="eliminar_producto"),

    # Detalles del producto
    path("productos/detalle/<int:producto_id>/", views.detalle_producto, name="detalle_producto"),

    # Administrador: Gestión de lotes
    path("stock/lotes/<int:producto_id>/", views.detalle_lotes, name="detalle_lotes"),
    path("stock/agregar-lote/<int:producto_id>/", views.agregar_lote, name="agregar_lote"),  # Se pasa el producto_id
    
    path("stock/editar-lote/<int:lote_id>/", views.editar_lote, name="editar_lote"),
    path("stock/eliminar-lote/<int:lote_id>/", views.eliminar_lote, name="eliminar_lote"),

    # Vendedor: Agregar stock a un lote existente
    path("stock/agregar-stock/<int:lote_id>/", views.agregar_stock, name="agregar_stock"),  # Se pasa el lote_id

    # NUEVAS FUNCIONALIDADES - ADMIN
    path("alerta/bajo-stock/", views.productos_bajo_stock, name="productos_bajo_stock"),
    path("alerta/proximos-caducar/", views.lotes_proximos_caducar, name="lotes_proximos_caducar"),

    # Administrador: Gestión de proveedores
    path("proveedores/", views.listar_proveedores, name="listar_proveedores"),
    path("proveedores/agregar/", views.agregar_proveedor, name="agregar_proveedor"),
    path("proveedores/editar/<int:proveedor_id>/", views.editar_proveedor, name="editar_proveedor"),
    path("proveedores/eliminar/<int:proveedor_id>/", views.eliminar_proveedor, name="eliminar_proveedor"),
]
