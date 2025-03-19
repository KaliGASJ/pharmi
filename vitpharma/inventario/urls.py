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

    # Vendedor: Agregar stock
    path("stock/agregar/", views.agregar_stock, name="agregar_stock"),

    # Administrador: Gestión de stock
    path("stock/gestionar/<int:producto_id>/", views.gestionar_stock, name="gestionar_stock"),

    # Administrador: Historial de modificaciones
    path("historial/", views.historial_modificaciones, name="historial_modificaciones"),
]
