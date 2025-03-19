from django.urls import path
from . import views as auth_views  # Alias para evitar posibles conflictos en otras apps

# Nombre de la app para su uso en `namespaces`
app_name = 'authapp'

urlpatterns = [
    # -------------------- AUTENTICACIÓN --------------------
    path('login/', auth_views.user_login, name='login'),
    path('logout/', auth_views.user_logout, name='logout'),

    # -------------------- DASHBOARDS --------------------
    path('admin_dashboard/', auth_views.admin_dashboard, name='admin_dashboard'),
    path('vendedor_dashboard/', auth_views.vendedor_dashboard, name='vendedor_dashboard'),

    # -------------------- ADMINISTRACIÓN DE USUARIOS --------------------
    path('usuarios/', auth_views.admin_usuarios, name='admin_usuarios'),
    path('usuarios/agregar/', auth_views.agregar_usuario, name='agregar_usuario'),
    path('usuarios/editar/<int:usuario_id>/', auth_views.editar_usuario, name='editar_usuario'),
    path('usuarios/eliminar/<int:usuario_id>/', auth_views.eliminar_usuario, name='eliminar_usuario'),

    # -------------------- MÓDULOS DEL ADMINISTRADOR --------------------
    path('inventario/', auth_views.admin_inventario, name='admin_inventario'),
    path('reportes/', auth_views.admin_reportes, name='admin_reportes'),
    path('proveedores/', auth_views.admin_proveedores, name='admin_proveedores'),
    path('soporte/', auth_views.admin_soporte, name='admin_soporte'),
]



