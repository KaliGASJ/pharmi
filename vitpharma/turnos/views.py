from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from django.http import HttpResponse
from .models import Turno
from .forms import IniciarTurnoForm
from ventas.models import Venta

# Verifica si el usuario pertenece al grupo "vendedor"
def es_vendedor(user):
    return user.is_authenticated and user.groups.filter(name='vendedor').exists()

@login_required
@user_passes_test(es_vendedor)
def turno_vendedor(request):
    usuario = request.user
    
    # Verificar si el usuario tiene un turno activo
    turno_activo = Turno.objects.filter(usuario=usuario, esta_activo=True).first()
    
    # Historial general de turnos finalizados con PDF
    historial_turnos = Turno.objects.filter(
        usuario=usuario,
        esta_activo=False,
        archivo_corte__isnull=False
    ).order_by('-fecha', '-hora_inicio')
    
    # Filtro por fecha desde GET
    fecha_filtrada = request.GET.get('fecha')
    if fecha_filtrada:
        try:
            fecha_obj = datetime.strptime(fecha_filtrada, "%Y-%m-%d").date()
            historial_turnos = historial_turnos.filter(fecha=fecha_obj)
        except ValueError:
            messages.warning(request, "Formato de fecha inválido. Usa el formato AAAA-MM-DD.")
    
    # Último turno finalizado con PDF (siempre actualizado)
    ultimo_turno_pdf = Turno.objects.filter(
        usuario=usuario,
        esta_activo=False,
        archivo_corte__isnull=False
    ).order_by('-modificado_en').first()
    
    if turno_activo:
        # Obtener ventas del turno actual
        ventas_turno = turno_activo.obtener_ventas()
        total_ventas_turno = turno_activo.total_ventas()
        
        return render(request, 'turno_vendedor.html', {
            'turno': turno_activo,
            'en_turno': True,
            'historial': historial_turnos,
            'fecha_filtrada': fecha_filtrada,
            'ultimo_turno_pdf': ultimo_turno_pdf,
            'ventas_turno': ventas_turno,
            'total_ventas_turno': total_ventas_turno,
            'cantidad_ventas': turno_activo.cantidad_ventas(),
        })
    
    # Si no hay turno activo, mostrar formulario
    if request.method == 'POST':
        form = IniciarTurnoForm(request.POST)
        if form.is_valid():
            nuevo_turno = form.save(commit=False)
            nuevo_turno.usuario = usuario
            nuevo_turno.esta_activo = True
            nuevo_turno.save()
            messages.success(request, "Has iniciado tu turno correctamente.")
            return redirect('turnos:turno_vendedor')
    else:
        # Inicializamos el formulario solo con la hora actual para inicio
        ahora = timezone.localtime()
        
        initial_data = {
            'hora_inicio': ahora.strftime('%H:%M'),
            # No se establece hora_fin para que el usuario la ingrese manualmente
            'monto_inicial': 0.00
        }
        form = IniciarTurnoForm(initial=initial_data)
    
    return render(request, 'turno_vendedor.html', {
        'form': form,
        'turno': None,
        'en_turno': False,
        'historial': historial_turnos,
        'fecha_filtrada': fecha_filtrada,
        'ultimo_turno_pdf': ultimo_turno_pdf,
    })

@login_required
@user_passes_test(es_vendedor)
def finalizar_turno(request):
    usuario = request.user
    turno_activo = Turno.objects.filter(usuario=usuario, esta_activo=True).first()
    
    if not turno_activo:
        messages.error(request, "No tienes un turno activo para finalizar.")
        return redirect('turnos:turno_vendedor')
    
    # Agregar validación para confirmar (GET muestra confirmación, POST procesa)
    if request.method != 'POST' and 'confirmar' not in request.GET:
        # Mostrar página de confirmación
        ventas_turno = turno_activo.obtener_ventas()
        total_ventas = turno_activo.total_ventas()
        
        return render(request, 'confirmar_finalizar_turno.html', {
            'turno': turno_activo,
            'ventas_turno': ventas_turno,
            'total_ventas': total_ventas,
            'cantidad_ventas': turno_activo.cantidad_ventas(),
        })
    
    # Calcular total de ventas del turno usando el método del modelo
    total_ventas = turno_activo.total_ventas()
    
    # Finalizar turno y generar PDF
    turno_activo.monto_final = total_ventas
    turno_activo.esta_activo = False
    turno_activo.generar_corte_caja_pdf()
    turno_activo.save()
    
    messages.success(request, "Turno finalizado correctamente. Se generó el corte de caja.")
    return redirect('turnos:turno_vendedor')

@login_required
@user_passes_test(es_vendedor)
def descargar_corte(request, turno_id):
    """Permite descargar el corte de caja directamente"""
    turno = get_object_or_404(Turno, id=turno_id, usuario=request.user)
    
    if not turno.archivo_corte:
        messages.error(request, "Este turno no tiene un corte de caja generado.")
        return redirect('turnos:turno_vendedor')
    
    response = HttpResponse(turno.archivo_corte.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{turno.archivo_corte.name.split("/")[-1]}"'
    return response

@login_required
@user_passes_test(es_vendedor)
def detalle_turno(request, turno_id):
    """Muestra el detalle completo de un turno incluyendo sus ventas"""
    turno = get_object_or_404(Turno, id=turno_id, usuario=request.user)
    ventas = turno.obtener_ventas()
    
    return render(request, 'detalle_turno.html', {
        'turno': turno,
        'ventas': ventas,
        'total_ventas': turno.total_ventas(),
        'cantidad_ventas': turno.cantidad_ventas(),
    })