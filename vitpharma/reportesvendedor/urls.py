from django.urls import path
from . import views

app_name = 'reportesvendedor'

urlpatterns = [
    path('', views.reportes_inicio, name='reportes_inicio'),
]
