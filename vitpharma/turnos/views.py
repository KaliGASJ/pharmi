from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum

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

    # Verificar si el usuario ya tiene un turno activo
    turno_activo = Turno.objects.filter(usuario=usuario, esta_activo=True).first()

    # Obtener historial general de turnos finalizados con PDF
    historial_turnos = Turno.objects.filter(
        usuario=usuario,
        esta_activo=False,
        archivo_corte__isnull=False
    ).order_by('-fecha', '-hora_inicio')

    # Filtro por fecha (si el usuario la proporciona en GET)
    fecha_filtrada = request.GET.get('fecha')
    if fecha_filtrada:
        try:
            fecha_obj = datetime.strptime(fecha_filtrada, "%Y-%m-%d").date()
            historial_turnos = historial_turnos.filter(fecha=fecha_obj)
        except ValueError:
            messages.warning(request, "Formato de fecha inválido. Usa el formato AAAA-MM-DD.")

    # Obtener el último turno con PDF generado, para botón de descarga
    ultimo_turno_pdf = Turno.objects.filter(
        usuario=usuario,
        esta_activo=False,
        archivo_corte__isnull=False
    ).order_by('-fecha', '-hora_inicio').first()

    # Si hay turno activo, se muestra turno activo
    if turno_activo:
        return render(request, 'turno_vendedor.html', {
            'turno': turno_activo,
            'en_turno': True,
            'historial': historial_turnos,
            'fecha_filtrada': fecha_filtrada,
            'ultimo_turno_pdf': ultimo_turno_pdf,
        })

    # No hay turno activo → mostrar formulario
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
        form = IniciarTurnoForm()

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

    # Calcular el total de ventas del turno
    ventas_turno = Venta.objects.filter(turno=turno_activo)
    total_ventas = ventas_turno.aggregate(Sum('total'))['total__sum'] or 0.00

    # Finalizar el turno y generar el archivo PDF
    turno_activo.monto_final = total_ventas
    turno_activo.esta_activo = False
    turno_activo.generar_corte_caja_pdf()
    turno_activo.save()

    messages.success(request, "Turno finalizado correctamente. Se generó el corte de caja.")
    return redirect('turnos:turno_vendedor')
