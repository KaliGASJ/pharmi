from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Turno
from .forms import AperturaTurnoForm, FinalizarTurnoForm


# -------------------- VERIFICADOR DE ROL --------------------

def es_vendedor(user):
    return user.is_authenticated and user.groups.filter(name='vendedor').exists()


# -------------------- DASHBOARD DEL MÓDULO DE TURNOS --------------------

@login_required
@user_passes_test(es_vendedor)
def turno_dashboard(request):
    turno_activo = Turno.obtener_turno_activo(request.user)
    if turno_activo:
        # Verificación automática por fecha/hora
        if turno_activo.verificar_finalizacion_automatica():
            messages.warning(request, "Tu turno fue cerrado automáticamente por haber superado la hora estimada.")
            return redirect('turnos:historial_turnos')
    return render(request, 'turno_dashboard.html', {
        'turno_activo': turno_activo
    })


# -------------------- ABRIR TURNO --------------------

@login_required
@user_passes_test(es_vendedor)
def abrir_turno(request):
    turno_existente = Turno.obtener_turno_activo(request.user)
    if turno_existente:
        messages.info(request, "Ya tienes un turno activo.")
        return redirect('turnos:turno_dashboard')

    if request.method == 'POST':
        form = AperturaTurnoForm(request.POST)
        if form.is_valid():
            nuevo_turno = form.save(commit=False)

            # Seguridad adicional: validar también en la vista (doble capa)
            if nuevo_turno.hora_fin_estimada <= timezone.now():
                messages.error(request, "La hora estimada de cierre debe ser posterior al momento actual.")
                return render(request, 'abrir_turno.html', {'form': form})

            nuevo_turno.usuario = request.user
            nuevo_turno.save()
            messages.success(request, "Turno iniciado correctamente.")
            return redirect('turnos:turno_dashboard')
    else:
        form = AperturaTurnoForm()

    return render(request, 'abrir_turno.html', {'form': form})


# -------------------- CERRAR TURNO --------------------

@login_required
@user_passes_test(es_vendedor)
def cerrar_turno(request):
    turno = Turno.obtener_turno_activo(request.user)
    if not turno:
        messages.error(request, "No tienes un turno activo.")
        return redirect('turnos:turno_dashboard')

    if request.method == 'POST':
        form = FinalizarTurnoForm(request.POST, instance=turno)
        if form.is_valid():
            turno = form.save(commit=False)
            turno.finalizar(hora_fin_real=turno.hora_fin_real)
            messages.success(request, "Turno cerrado correctamente.")
            return redirect('turnos:historial_turnos')
    else:
        form = FinalizarTurnoForm(instance=turno)

    return render(request, 'cerrar_turno.html', {'form': form, 'turno': turno})


# -------------------- HISTORIAL DE TURNOS --------------------

@login_required
@user_passes_test(es_vendedor)
def historial_turnos(request):
    turnos = Turno.objects.filter(usuario=request.user, estado='finalizado').order_by('-hora_inicio')

    # Filtro por fechas (opcional)
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio_dt = timezone.datetime.fromisoformat(fecha_inicio)
            fecha_fin_dt = timezone.datetime.fromisoformat(fecha_fin)
            turnos = turnos.filter(hora_inicio__range=(fecha_inicio_dt, fecha_fin_dt))
        except:
            messages.error(request, "Formato de fecha inválido.")

    sin_resultados = not turnos.exists()

    return render(request, 'historial_turnos.html', {
        'turnos': turnos,
        'sin_resultados': sin_resultados
    })


# -------------------- DETALLE DE UN TURNO --------------------

@login_required
@user_passes_test(es_vendedor)
def detalle_turno(request, turno_id):
    turno = get_object_or_404(Turno, id=turno_id, usuario=request.user)
    return render(request, 'detalle_turno.html', {'turno': turno})


# -------------------- DESCARGAR PDF DEL CORTE --------------------

@login_required
@user_passes_test(es_vendedor)
def descargar_pdf_turno(request, turno_id):
    turno = get_object_or_404(Turno, id=turno_id, usuario=request.user)

    if not turno.pdf_reporte or not turno.pdf_reporte.path:
        raise Http404("Este turno no tiene un reporte PDF generado.")

    try:
        with open(turno.pdf_reporte.path, 'rb') as pdf:
            response = HttpResponse(pdf.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="corte_turno_{turno.id}.pdf"'
            return response
    except FileNotFoundError:
        raise Http404("El archivo PDF no fue encontrado.")
