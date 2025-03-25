from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib import messages
from weasyprint import HTML
from django.utils import timezone
import os

from turnos.models import Turno
from .models import Venta, DetalleVenta
from .forms import VentaForm, DetalleVentaFormSet


# -------------------- VERIFICAR SI ES VENDEDOR --------------------

def es_vendedor(user):
    return user.is_authenticated and user.groups.filter(name='vendedor').exists()


# -------------------- DASHBOARD DE REGISTRO DE VENTAS --------------------

@login_required
@user_passes_test(es_vendedor)
def venta_dashboard(request):
    turno_activo = Turno.objects.filter(usuario=request.user, estado='activo').first()
    if not turno_activo:
        messages.warning(request, "Debes iniciar un turno antes de realizar ventas.")
        return redirect('turnos:turno_dashboard')

    if request.method == 'POST':
        form_venta = VentaForm(request.POST)
        formset_detalles = DetalleVentaFormSet(request.POST)

        if form_venta.is_valid() and formset_detalles.is_valid():
            venta = form_venta.save(commit=False)
            venta.usuario = request.user
            venta.turno = turno_activo
            venta.fecha_hora = timezone.now()
            venta.total = 0  # Se calculará luego

            venta.save()

            total = 0
            for form in formset_detalles:
                detalle = form.save(commit=False)
                detalle.venta = venta
                detalle.subtotal = detalle.calcular_subtotal()
                detalle.lote.consumir_stock(detalle.cantidad)
                detalle.save()
                total += detalle.subtotal

            venta.total = total

            # Cálculo del cambio (solo efectivo)
            metodo = venta.metodo_pago.nombre.lower()
            if "efectivo" in metodo:
                con_cuanto_paga = form_venta.cleaned_data.get('con_cuanto_paga')
                cambio = con_cuanto_paga - total if con_cuanto_paga else 0
                venta.con_cuanto_paga = con_cuanto_paga
                venta.cambio = max(cambio, 0)
                turno_activo.total_cambios_dados += venta.cambio
                turno_activo.monto_total_efectivo += total
            elif "tarjeta" in metodo:
                turno_activo.monto_total_tarjeta += total
            elif "transferencia" in metodo:
                turno_activo.monto_total_transferencia += total
            elif "cheque" in metodo:
                turno_activo.monto_total_cheque += total

            venta.save()
            turno_activo.save()

            messages.success(request, "Venta registrada correctamente.")
            return redirect('ventas:generar_ticket_pdf', venta.id)

        else:
            messages.error(request, "Error al registrar la venta. Revisa los campos.")
    else:
        form_venta = VentaForm()
        formset_detalles = DetalleVentaFormSet(queryset=DetalleVenta.objects.none())

    return render(request, 'venta_dashboard.html', {
        'form_venta': form_venta,
        'formset_detalles': formset_detalles
    })


# -------------------- CANCELAR VENTA --------------------

@login_required
@user_passes_test(es_vendedor)
def cancelar_venta(request):
    messages.info(request, "Venta cancelada.")
    return redirect('ventas:venta_dashboard')


# -------------------- HISTORIAL DE VENTAS --------------------

@login_required
@user_passes_test(es_vendedor)
def historial_ventas(request):
    ventas = Venta.objects.filter(usuario=request.user).order_by('-fecha_hora')
    return render(request, 'historial_ventas.html', {'ventas': ventas})


# -------------------- DETALLE INDIVIDUAL DE VENTA --------------------

@login_required
@user_passes_test(es_vendedor)
def detalle_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id, usuario=request.user)
    detalles = venta.detalles.all()
    return render(request, 'detalle_venta.html', {
        'venta': venta,
        'detalles': detalles
    })


# -------------------- GENERAR TICKET PDF --------------------

@login_required
@user_passes_test(es_vendedor)
def generar_ticket_pdf(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id, estado='activa')
    detalles = venta.detalles.all()

    context = {
        'venta': venta,
        'detalles': detalles,
        'usuario': venta.usuario,
        'fecha': venta.fecha_hora,
        'total': venta.total,
        'con_cuanto_paga': venta.con_cuanto_paga,
        'cambio': venta.cambio,
        'metodo_pago': venta.metodo_pago.nombre if venta.metodo_pago else "N/A",
        'farmacia_nombre': "Farmacia Vital",
        'mensaje_gracias': "¡Gracias por su compra!",
    }

    html_string = render_to_string('ticket_venta.html', context)
    pdf_file = HTML(string=html_string).write_pdf()

    nombre_archivo = f"venta_{venta.id}_{venta.usuario.username}.pdf"
    ruta_archivo = os.path.join(settings.MEDIA_ROOT, 'tickets', nombre_archivo)
    os.makedirs(os.path.dirname(ruta_archivo), exist_ok=True)

    with open(ruta_archivo, 'wb') as f:
        f.write(pdf_file)

    venta.ticket_pdf.name = f"tickets/{nombre_archivo}"
    venta.save(update_fields=["ticket_pdf"])

    with open(ruta_archivo, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{nombre_archivo}"'
        return response
