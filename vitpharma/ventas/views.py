from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, Http404, JsonResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from decimal import Decimal
import json

from .models import Venta, DetalleVenta
from .forms import VentaForm, CancelarVentaForm
from turnos.models import Turno
from inventario.models import Producto, InventarioProducto


# -------------------- VERIFICAR SI ES VENDEDOR --------------------

def es_vendedor(user):
    return user.is_authenticated and user.groups.filter(name='vendedor').exists()


# -------------------- DASHBOARD DE VENTAS --------------------

@login_required
@user_passes_test(es_vendedor)
def venta_dashboard(request):
    turno = Turno.obtener_turno_activo(request.user)
    if not turno:
        messages.warning(request, "Debes iniciar un turno antes de registrar ventas.")
        return redirect('turnos:abrir_turno')

    venta_form = VentaForm()

    return render(request, 'registro_venta.html', {
        'venta_form': venta_form,
        'turno': turno
    })


# -------------------- API: BUSCADOR DE PRODUCTOS Y LOTES DISPONIBLES --------------------

@login_required
@user_passes_test(es_vendedor)
def api_buscar_productos(request):
    query = request.GET.get("q", "").strip()
    resultados = []

    if query:
        productos = Producto.objects.filter(nombre__icontains=query, estado='activo')
        for producto in productos:
            lotes = InventarioProducto.objects.filter(
                producto=producto,
                cantidad__gt=0,
                fecha_caducidad__gte=timezone.now().date()
            ).order_by("fecha_caducidad")

            lotes_data = []
            for lote in lotes:
                precio_final = lote.precio_venta
                if lote.descuento_porcentaje:
                    precio_final -= (precio_final * (lote.descuento_porcentaje / 100))

                lotes_data.append({
                    "lote_id": lote.id_inventario,
                    "lote": lote.lote,
                    "stock": lote.cantidad,
                    "precio": float(lote.precio_venta),
                    "descuento": float(lote.descuento_porcentaje or 0),
                    "precio_final": float(round(precio_final, 2)),
                    "caducidad": lote.fecha_caducidad.strftime("%d/%m/%Y"),
                })

            resultados.append({
                "producto_id": producto.id_producto,
                "nombre": producto.nombre,
                "codigo_barras": producto.codigo_barras,
                "lotes": lotes_data
            })

    return JsonResponse({"resultados": resultados})


# -------------------- PROCESAR VENTA --------------------

@login_required
@user_passes_test(es_vendedor)
def procesar_venta(request):
    turno = Turno.obtener_turno_activo(request.user)
    if not turno:
        messages.error(request, "No hay un turno activo.")
        return redirect('ventas:venta_dashboard')

    if request.method == 'POST':
        venta_form = VentaForm(request.POST)
        if venta_form.is_valid():
            venta = venta_form.save(commit=False)
            venta.usuario = request.user
            venta.turno = turno
            venta.usuario_registro = request.user
            venta.save()

            carrito_json = request.POST.get("carrito_json")
            if carrito_json:
                try:
                    carrito = json.loads(carrito_json)
                    for item in carrito:
                        producto_id = item.get("producto_id")
                        lote_id = item.get("lote_id")
                        cantidad = int(item.get("cantidad"))
                        precio_unitario = Decimal(str(item.get("precio_unitario")))
                        subtotal = Decimal(str(item.get("subtotal")))

                        DetalleVenta.objects.create(
                            venta=venta,
                            producto_id=producto_id,
                            lote_id=lote_id,
                            cantidad=cantidad,
                            precio_unitario=precio_unitario,
                            subtotal=subtotal
                        )

                        lote = InventarioProducto.objects.get(id_inventario=lote_id)
                        lote.cantidad -= cantidad
                        lote.save(update_fields=["cantidad"])

                    venta.actualizar_totales()

                except Exception as e:
                    venta.delete()
                    messages.error(request, f"Error al procesar el carrito: {str(e)}")
                    return redirect('ventas:venta_dashboard')

            messages.success(request, f"✅ Venta #{venta.id} registrada correctamente.")
            return redirect('ventas:detalle_venta', venta.id)

        messages.error(request, "Error en los datos de la venta.")

    return redirect("ventas:venta_dashboard")


# -------------------- DETALLE DE VENTA --------------------

@login_required
@user_passes_test(es_vendedor)
def detalle_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id, usuario=request.user)
    detalles = venta.detalles.all()
    return render(request, 'detalle_venta.html', {
        'venta': venta,
        'detalles': detalles
    })


# -------------------- HISTORIAL DE VENTAS --------------------

@login_required
@user_passes_test(es_vendedor)
def historial_ventas(request):
    ventas = Venta.objects.filter(usuario=request.user).order_by('-fecha_hora')
    return render(request, 'historial_ventas.html', {'ventas': ventas})


# -------------------- CANCELAR VENTA --------------------

@login_required
@user_passes_test(es_vendedor)
def cancelar_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id, usuario=request.user)

    if venta.estado != 'activa':
        messages.warning(request, "Esta venta ya fue cancelada.")
        return redirect('ventas:detalle_venta', venta.id)

    if request.method == 'POST':
        form = CancelarVentaForm(request.POST)
        if form.is_valid():
            venta.cancelar()
            messages.success(request, f"La venta #{venta.id} ha sido cancelada.")
            return redirect('ventas:detalle_venta', venta.id)
    else:
        form = CancelarVentaForm()

    return render(request, 'cancelar_venta.html', {
        'venta': venta,
        'form': form
    })


# -------------------- GENERAR TICKET PDF --------------------

@login_required
@user_passes_test(es_vendedor)
def generar_ticket_pdf(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id, usuario=request.user)
    if not venta.ticket_pdf:
        html_string = render_to_string('ticket_venta.html', {'venta': venta})
        pdf_file = HTML(string=html_string).write_pdf()
        filename = f"ticket_venta_{venta.id}_{venta.usuario.username}.pdf"
        venta.ticket_pdf.save(filename, pdf_file)
        venta.save(update_fields=['ticket_pdf'])

    if venta.ticket_pdf:
        with open(venta.ticket_pdf.path, 'rb') as pdf:
            response = HttpResponse(pdf.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="ticket_{venta.id}.pdf"'
            return response

    raise Http404("El ticket no se pudo generar.")


# -------------------- API JSON: ÚLTIMAS VENTAS --------------------

@login_required
@user_passes_test(es_vendedor)
def ventas_api_json(request):
    ventas = Venta.objects.filter(usuario=request.user).order_by('-fecha_hora')[:20]
    data = [
        {
            'id': v.id,
            'total': str(v.total),
            'metodo_pago': v.metodo_pago.nombre if v.metodo_pago else '',
            'fecha': v.fecha_hora.strftime('%d/%m/%Y %H:%M'),
            'estado': v.estado
        }
        for v in ventas
    ]
    return JsonResponse({'ventas': data})


# -------------------- FILTRO DE VENTAS POR FECHA --------------------

@login_required
@user_passes_test(es_vendedor)
def ventas_por_fecha(request):
    fecha_inicio = request.GET.get('inicio')
    fecha_fin = request.GET.get('fin')

    ventas = Venta.objects.filter(usuario=request.user)

    if fecha_inicio:
        ventas = ventas.filter(fecha_hora__gte=fecha_inicio)
    if fecha_fin:
        ventas = ventas.filter(fecha_hora__lte=fecha_fin)

    ventas = ventas.order_by('-fecha_hora')

    return render(request, 'ventas_filtradas.html', {
        'ventas': ventas,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    })
