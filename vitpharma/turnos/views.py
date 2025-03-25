from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib import messages
from weasyprint import HTML
from datetime import datetime, date
import os

from .models import Turno
from ventas.models import Venta
from .forms import IniciarTurnoForm, FinalizarTurnoForm, FiltroTurnoForm


# -------------------- VERIFICADOR DE ROL --------------------

def es_vendedor(user):
    return user.is_authenticated and user.groups.filter(name='vendedor').exists()


# -------------------- DASHBOARD DEL MÓDULO DE TURNOS --------------------

@login_required
@user_passes_test(es_vendedor)
def turno_dashboard(request):
    # Verificar si hay algún turno activo que ya expiró
    turno_activo = Turno.obtener_turno_activo(request.user)
    
    # Verificar finalización automática de turnos expirados
    if turno_activo and turno_activo.ha_expirado():
        messages.warning(request, "Se ha detectado un turno expirado que no fue cerrado correctamente.")
    
    # Filtrar turnos por fecha si se especifica
    fecha_filtro = None
    
    if request.method == 'GET' and 'fecha' in request.GET:
        form_filtro = FiltroTurnoForm(request.GET)
        if form_filtro.is_valid():
            fecha_filtro = form_filtro.cleaned_data['fecha']
            turnos_finalizados = Turno.obtener_turnos_por_fecha(request.user, fecha_filtro)
            
            if not turnos_finalizados.exists():
                messages.info(request, f"No hay turnos registrados para la fecha {fecha_filtro.strftime('%d/%m/%Y')}.")
    else:
        form_filtro = FiltroTurnoForm()
        turnos_finalizados = Turno.objects.filter(usuario=request.user, estado='finalizado').order_by('-hora_inicio')
    
    # Obtener ventas del turno activo
    ventas_turno = Venta.objects.filter(turno=turno_activo, usuario=request.user).order_by('-fecha_hora') if turno_activo else []
    
    context = {
        'turno_activo': turno_activo,
        'turnos_finalizados': turnos_finalizados,
        'ventas_turno': ventas_turno,
        'form_filtro': form_filtro,
        'fecha_filtro': fecha_filtro,
        'fecha_actual': date.today(),
    }
    
    return render(request, 'turno_dashboard.html', context)


# -------------------- INICIAR TURNO --------------------

@login_required
@user_passes_test(es_vendedor)
def iniciar_turno(request):
    # Verificar si ya existe un turno activo
    if Turno.objects.filter(usuario=request.user, estado='activo').exists():
        messages.warning(request, "Ya tienes un turno activo. Debes finalizarlo antes de iniciar otro.")
        return redirect('turnos:turno_dashboard')

    if request.method == 'POST':
        form = IniciarTurnoForm(request.POST)
        if form.is_valid():
            turno = form.save(commit=False)
            turno.usuario = request.user
            turno.hora_inicio = timezone.now()
            turno.save()
            
            messages.success(request, f"Turno iniciado correctamente con ${turno.monto_inicial} en caja.")
            return redirect('turnos:turno_dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")
    else:
        # Crear formulario con valores iniciales
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
            
            # Obtener observaciones si existen
            observaciones = form.cleaned_data.get('observaciones', '')

            # Recalcular totales
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
                'observaciones': observaciones,
                'farmacia': "Farmacia Vital",
                'fecha_generacion': timezone.now(),
            }

            # Generar PDF de corte
            html = render_to_string('corte_turno.html', context)
            pdf = HTML(string=html).write_pdf()
            filename = f"turno_{turno.id}_{request.user.username}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(settings.MEDIA_ROOT, 'cortes_cajas', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, 'wb') as f:
                f.write(pdf)

            turno.pdf_reporte.name = f"cortes_cajas/{filename}"
            turno.estado = 'finalizado'
            turno.save()
            
            messages.success(request, "Turno finalizado correctamente. Se ha generado el corte de caja.")
            return redirect('turnos:turno_dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")

    else:
        form = FinalizarTurnoForm(initial={'hora_fin_real': timezone.now()})

    return render(request, 'finalizar_turno.html', {'form': form, 'turno': turno})


# -------------------- DESCARGAR PDF DEL CORTE --------------------

@login_required
@user_passes_test(es_vendedor)
def descargar_corte_pdf(request, turno_id):
    turno = get_object_or_404(Turno, id=turno_id, usuario=request.user, estado='finalizado')
    if not turno.pdf_reporte:
        messages.error(request, "PDF no disponible. El reporte no se generó correctamente.")
        return redirect('turnos:turno_dashboard')

    try:
        ruta_archivo = os.path.join(settings.MEDIA_ROOT, turno.pdf_reporte.name)
        with open(ruta_archivo, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{os.path.basename(ruta_archivo)}"'
            return response
    except FileNotFoundError:
        messages.error(request, "No se pudo encontrar el archivo PDF del corte de caja.")
        return redirect('turnos:turno_dashboard')


# -------------------- OBTENER DATOS DE EFECTIVO EN CAJA (AJAX) --------------------

@login_required
@user_passes_test(es_vendedor)
def obtener_efectivo_caja(request):
    """
    Vista para solicitudes AJAX que devuelve datos actualizados del efectivo en caja
    """
    turno_activo = Turno.obtener_turno_activo(request.user)
    
    if not turno_activo:
        return JsonResponse({
            'success': False,
            'message': 'No hay turno activo'
        })
    
    datos = {
        'success': True,
        'monto_inicial': float(turno_activo.monto_inicial),
        'monto_efectivo': float(turno_activo.monto_total_efectivo),
        'cambios_dados': float(turno_activo.total_cambios_dados),
        'efectivo_en_caja': float(turno_activo.efectivo_en_caja()),
        'efectivo_final': float(turno_activo.efectivo_final_en_caja()),
        'timestamp': timezone.now().isoformat()
    }
    
    return JsonResponse(datos)


# -------------------- FILTRAR TURNOS POR FECHA --------------------

@login_required
@user_passes_test(es_vendedor)
def filtrar_turnos(request):
    """
    Vista dedicada para filtrar turnos por fecha
    """
    if request.method == 'GET':
        form = FiltroTurnoForm(request.GET)
        if form.is_valid():
            fecha = form.cleaned_data['fecha']
            turnos = Turno.obtener_turnos_por_fecha(request.user, fecha)
            
            context = {
                'turnos': turnos,
                'fecha': fecha,
                'form': form
            }
            
            return render(request, 'turnos_filtrados.html', context)
    else:
        form = FiltroTurnoForm()
    
    return render(request, 'filtrar_turnos.html', {'form': form})