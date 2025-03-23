from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('authapp.urls')),  # Rutas de autenticación y usuarios
    path('inventario/', include('inventario.urls')),  # Rutas de la app inventario
    path('inventario-vendedor/', include('inventariovendedor.urls')),  # Rutas de la app inventariovendedor
    path('turno/', include('turnos.urls')),  # Rutas de la app turnos
    path('ventas/', include('ventas.urls')),  # Rutas de la app ventas
    path('reportes/', include('reportes.urls')),  # Rutas de la app reportes
    path('consultas/', include('consultas.urls')),  # Rutas de la app consultas
    path('reportesvendedor/', include('reportesvendedor.urls')),  # Rutas de la app reportesvendedor
    path('soportevendedor/', include('soportevendedor.urls')),  # Rutas de la app soportevendedor
]

# Para servir archivos MEDIA (PDFs, imágenes subidas, etc.) durante el desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
