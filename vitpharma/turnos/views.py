from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML
import os

from .models import Turno
from ventas.models import Venta
from .forms import IniciarTurnoForm, FinalizarTurnoForm


# -------------------- VERIFICADOR DE ROL --------------------

def es_vendedor(user):
    return user.is_authenticated and user.groups.filter(name='vendedor').exists()


# -------------------- DASHBOARD DEL MÓDULO DE TURNOS --------------------

@login_required
@user_passes_test(es_vendedor)
def turno_dashboard(request):
    turno_activo = Turno.objects.filter(usuario=request.user, estado='activo').first()
    turnos_finalizados = Turno.objects.filter(usuario=request.user, estado='finalizado').order_by('-hora_inicio')
    ventas_turno = Venta.objects.filter(turno=turno_activo, usuario=request.user) if turno_activo else []

    context = {
        'turno_activo': turno_activo,
        'turnos_finalizados': turnos_finalizados,
        'ventas_turno': ventas_turno,
    }
    return render(request, 'turno_dashboard.html', context)


# -------------------- INICIAR TURNO --------------------

@login_required
@user_passes_test(es_vendedor)
def iniciar_turno(request):
    if Turno.objects.filter(usuario=request.user, estado='activo').exists():
        return redirect('turnos:turno_dashboard')

    if request.method == 'POST':
        form = IniciarTurnoForm(request.POST)
        if form.is_valid():
            turno = form.save(commit=False)
            turno.usuario = request.user
            turno.save()
            return redirect('turnos:turno_dashboard')
    else:
        form = IniciarTurnoForm()

    return render(request, 'iniciar_turno.html', {'form': form})


# -------------------- FINALIZAR TURNO --------------------

@login_required
@user_passes_test(es_vendedor)
def finalizar_turno(request, turno_id):
    turno = get_object_or_404(Turno, id=turno_id, usuario=request.user, estado='activo')

    if request.method == 'POST':
        form = FinalizarTurnoForm(request.POST, instance=turno)
        if form.is_valid():
            # Preparar para finalizar turno y generar corte
            turno = form.save(commit=False)
            turno.hora_fin_real = timezone.now()

            # Recalcular totales por si se editaron manualmente (opcional)
            total_turno = turno.total_ventas_turno()
            efectivo_en_caja = turno.efectivo_en_caja()
            efectivo_final = turno.efectivo_final_en_caja()

            context = {
                'turno': turno,
                'usuario': request.user,
                'fecha_inicio': turno.hora_inicio,
                'fecha_fin': turno.hora_fin_real,
                'monto_inicial': turno.monto_inicial,
                'monto_efectivo': turno.monto_total_efectivo,
                'monto_tarjeta': turno.monto_total_tarjeta,
                'monto_transferencia': turno.monto_total_transferencia,
                'monto_cheque': turno.monto_total_cheque,
                'total_turno': total_turno,
                'cambios_dados': turno.total_cambios_dados,
                'efectivo_en_caja': efectivo_en_caja,
                'efectivo_final_en_caja': efectivo_final,
                'farmacia': "Farmacia Vital"
            }

            # Generar PDF de corte
            html = render_to_string('corte_turno.html', context)
            pdf = HTML(string=html).write_pdf()
            filename = f"turno_{turno.id}_{request.user.username}.pdf"
            filepath = os.path.join(settings.MEDIA_ROOT, 'cortes_cajas', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, 'wb') as f:
                f.write(pdf)

            turno.pdf_reporte.name = f"cortes_cajas/{filename}"
            turno.estado = 'finalizado'
            turno.save()
            return redirect('turnos:turno_dashboard')

    else:
        form = FinalizarTurnoForm(initial={'hora_fin_real': timezone.now()})

    return render(request, 'finalizar_turno.html', {'form': form, 'turno': turno})


# -------------------- DESCARGAR PDF DEL CORTE --------------------

@login_required
@user_passes_test(es_vendedor)
def descargar_corte_pdf(request, turno_id):
    turno = get_object_or_404(Turno, id=turno_id, usuario=request.user, estado='finalizado')
    if not turno.pdf_reporte:
        return HttpResponse("PDF no disponible", status=404)

    ruta_archivo = os.path.join(settings.MEDIA_ROOT, turno.pdf_reporte.name)
    with open(ruta_archivo, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(ruta_archivo)}"'
        return response
