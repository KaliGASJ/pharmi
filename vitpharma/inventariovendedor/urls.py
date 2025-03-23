# inventariovendedor/urls.py

from django.urls import path
from . import views

app_name = 'inventariovendedor'

urlpatterns = [
    path('', views.inventario_vendedor_dashboard, name='inventario_vendedor_dashboard'),
]
