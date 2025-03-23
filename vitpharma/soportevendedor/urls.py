from django.urls import path
from . import views

app_name = 'soportevendedor'

urlpatterns = [
    path('', views.soporte_inicio, name='soporte_inicio'),
]
