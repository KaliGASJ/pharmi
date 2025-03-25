from django.urls import path
from . import views

app_name = 'turnos'

urlpatterns = [
    # Panel principal del módulo de turnos
    path('', views.turno_dashboard, name='turno_dashboard'),
    
    # Iniciar un nuevo turno
    path('iniciar/', views.iniciar_turno, name='iniciar_turno'),
    
    # Finalizar un turno activo
    path('finalizar/<int:turno_id>/', views.finalizar_turno, name='finalizar_turno'),
    
    # Descargar el PDF del corte de caja finalizado
    path('descargar-corte/<int:turno_id>/', views.descargar_corte_pdf, name='descargar_corte_pdf'),
    
    # Obtener datos del efectivo en caja (para actualización AJAX)
    path('efectivo-caja/', views.obtener_efectivo_caja, name='obtener_efectivo_caja'),
    
    # Filtrar turnos por fecha específica
    path('filtrar/', views.filtrar_turnos, name='filtrar_turnos'),
    
    # Ruta opcional para verificar turnos expirados (puede llamarse desde un cron job)
    path('verificar-turnos-expirados/', views.verificar_turnos_expirados, name='verificar_turnos_expirados'),
]