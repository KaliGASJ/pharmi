from django.urls import path
from . import views

app_name = 'turnos'

urlpatterns = [
    # Dashboard principal del módulo de turnos
    path('', views.turno_dashboard, name='turno_dashboard'),

    # Apertura de turno
    path('abrir/', views.abrir_turno, name='abrir_turno'),

    # Cierre de turno activo
    path('cerrar/', views.cerrar_turno, name='cerrar_turno'),

    # Historial de turnos finalizados (con posible filtro de fechas)
    path('historial/', views.historial_turnos, name='historial_turnos'),

    # Detalle de un turno específico
    path('detalle/<int:turno_id>/', views.detalle_turno, name='detalle_turno'),

    # Descargar el PDF del corte de caja
    path('descargar/<int:turno_id>/', views.descargar_pdf_turno, name='descargar_pdf_turno'),
]
