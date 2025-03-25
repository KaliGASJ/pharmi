from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db import transaction
from weasyprint import HTML
import os
import json
from decimal import Decimal

from turnos.models import Turno
from inventario.models import Producto, InventarioProducto
from .models import Venta, DetalleVenta, MetodoPago
from .forms import (
    VentaForm, DetalleVentaFormSet, BusquedaProductoForm,
    CarritoItemForm, BusquedaVentasForm
)


# -------------------- VERIFICAR SI ES VENDEDOR --------------------

def es_vendedor(user):
    return user.is_authenticated and user.groups.filter(name='vendedor').exists()


# -------------------- DASHBOARD DE REGISTRO DE VENTAS --------------------

@login_required
@user_passes_test(es_vendedor)
def venta_dashboard(request):
    turno_activo = Turno.obtener_turno_activo(request.user)
    
    # Verificar si existe un turno activo
    if not turno_activo:
        messages.warning(request, "Debes iniciar un turno antes de realizar ventas.")
        return redirect('turnos:turno_dashboard')
    
    # Buscar productos por nombre o código
    busqueda_form = BusquedaProductoForm(request.GET or None)
    productos = []
    
    if busqueda_form.is_valid() and busqueda_form.cleaned_data.get('busqueda'):
        termino = busqueda_form.cleaned_data.get('busqueda')
        productos = Producto.objects.filter(
            estado='activo'
        ).filter(
            nombre__icontains=termino
        ) | Producto.objects.filter(
            estado='activo',
            codigo_barras__icontains=termino
        )
        
        if not productos:
            messages.info(request, f"No se encontraron productos con '{termino}'")
    
    # Obtener métodos de pago para el formulario
    metodos_pago = MetodoPago.objects.all()
    
    if request.method == 'POST':
        # Procesar la venta
        form_venta = VentaForm(request.POST, turno=turno_activo, usuario=request.user)
        
        if form_venta.is_valid():
            try:
                with transaction.atomic():
                    # Guardar la venta
                    venta = form_venta.save()
                    
                    # Procesar el carrito desde JSON
                    carrito_json = form_venta.cleaned_data.get('carrito_json')
                    carrito = json.loads(carrito_json)
                    
                    # Crear detalles de venta desde el carrito
                    for item in carrito:
                        # Obtener objetos relacionados
                        producto = get_object_or_404(Producto, id_producto=item['producto_id'])
                        lote = get_object_or_404(InventarioProducto, id_inventario=item['lote_id'])
                        
                        # Crear detalle
                        detalle = DetalleVenta(
                            venta=venta,
                            producto=producto,
                            lote=lote,
                            cantidad=item['cantidad'],
                            precio_unitario=Decimal(str(item['precio_unitario'])),
                            descuento_aplicado=Decimal(str(item['descuento_aplicado'])),
                            subtotal=Decimal(str(item['subtotal']))
                        )
                        
                        # Consumir stock
                        lote.consumir_stock(detalle.cantidad)
                        
                        # Guardar detalle
                        detalle.save()
                    
                    # Registrar venta en el turno
                    venta.registrar_en_turno()
                    
                    messages.success(request, "Venta registrada correctamente.")
                    return redirect('ventas:generar_ticket_pdf', venta.id)
            
            except Exception as e:
                messages.error(request, f"Error al procesar la venta: {str(e)}")
        else:
            # Mostrar los errores del formulario
            for field, errors in form_venta.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")
    
    else:
        # Formulario inicial
        form_venta = VentaForm(turno=turno_activo, usuario=request.user)
    
    context = {
        'form_venta': form_venta,
        'busqueda_form': busqueda_form,
        'productos': productos,
        'metodos_pago': metodos_pago,
        'turno_activo': turno_activo,
        'efectivo_en_caja': turno_activo.efectivo_final_en_caja(),
    }
    
    return render(request, 'venta_dashboard.html', context)


# -------------------- OBTENER LOTES DE UN PRODUCTO (AJAX) --------------------

@login_required
@user_passes_test(es_vendedor)
def get_lotes_producto(request):
    """Vista AJAX para obtener los lotes disponibles de un producto"""
    
    producto_id = request.GET.get('producto_id')
    
    if not producto_id:
        return JsonResponse({'error': 'Producto no especificado'}, status=400)
    
    try:
        producto = Producto.objects.get(id_producto=producto_id)
        lotes = producto.get_lotes_disponibles()
        
        lotes_data = [{
            'id': lote.id_inventario,
            'codigo': lote.codigo_lote,
            'lote': lote.lote,
            'cantidad': lote.cantidad,
            'precio_venta': float(lote.precio_venta),
            'descuento_porcentaje': float(lote.descuento_porcentaje) if lote.descuento_porcentaje else 0,
            'fecha_caducidad': lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else 'N/A'
        } for lote in lotes]
        
        return JsonResponse({'lotes': lotes_data})
    
    except Producto.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -------------------- OBTENER INFORMACIÓN DE UN LOTE (AJAX) --------------------

@login_required
@user_passes_test(es_vendedor)
def get_info_lote(request):
    """Vista AJAX para obtener información detallada de un lote"""
    
    lote_id = request.GET.get('lote_id')
    
    if not lote_id:
        return JsonResponse({'error': 'Lote no especificado'}, status=400)
    
    try:
        lote = InventarioProducto.objects.get(id_inventario=lote_id)
        precio_venta = float(lote.precio_venta)
        descuento_porcentaje = float(lote.descuento_porcentaje) if lote.descuento_porcentaje else 0
        
        # Calcular precio con descuento
        descuento_monto = (precio_venta * descuento_porcentaje) / 100
        precio_con_descuento = precio_venta - descuento_monto
        
        data = {
            'producto_id': lote.producto.id_producto,
            'producto_nombre': lote.producto.nombre,
            'codigo_lote': lote.codigo_lote,
            'lote': lote.lote,
            'cantidad_disponible': lote.cantidad,
            'precio_venta': precio_venta,
            'descuento_porcentaje': descuento_porcentaje,
            'descuento_monto': descuento_monto,
            'precio_con_descuento': precio_con_descuento,
            'fecha_caducidad': lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else None
        }
        
        return JsonResponse(data)
    
    except InventarioProducto.DoesNotExist:
        return JsonResponse({'error': 'Lote no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -------------------- AGREGAR PRODUCTO AL CARRITO (AJAX) --------------------

@login_required
@user_passes_test(es_vendedor)
@require_POST
def agregar_al_carrito(request):
    """Vista AJAX para agregar un producto al carrito"""
    
    try:
        # Parsear datos del formulario
        producto_id = request.POST.get('producto_id')
        lote_id = request.POST.get('lote_id')
        cantidad = int(request.POST.get('cantidad', 1))
        
        # Validaciones básicas
        if not producto_id or not lote_id or cantidad < 1:
            return JsonResponse({
                'success': False,
                'message': 'Datos inválidos para agregar al carrito'
            }, status=400)
        
        # Obtener objetos
        producto = get_object_or_404(Producto, id_producto=producto_id)
        lote = get_object_or_404(InventarioProducto, id_inventario=lote_id)
        
        # Verificar stock
        if cantidad > lote.cantidad:
            return JsonResponse({
                'success': False,
                'message': f'Stock insuficiente. Disponible: {lote.cantidad}'
            }, status=400)
        
        # Calcular precios y subtotal
        precio_unitario = float(lote.precio_venta)
        descuento_porcentaje = float(lote.descuento_porcentaje) if lote.descuento_porcentaje else 0
        descuento_monto = (precio_unitario * descuento_porcentaje) / 100
        precio_con_descuento = precio_unitario - descuento_monto
        subtotal = precio_con_descuento * cantidad
        
        # Preparar respuesta
        item_data = {
            'producto_id': producto.id_producto,
            'producto_nombre': producto.nombre,
            'codigo_barras': producto.codigo_barras,
            'lote_id': lote.id_inventario,
            'lote_codigo': lote.codigo_lote,
            'lote_nombre': lote.lote,
            'cantidad': cantidad,
            'precio_unitario': precio_unitario,
            'descuento_porcentaje': descuento_porcentaje,
            'descuento_aplicado': descuento_monto,
            'precio_final': precio_con_descuento,
            'subtotal': subtotal
        }
        
        return JsonResponse({
            'success': True,
            'message': 'Producto agregado al carrito',
            'item': item_data
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)


# -------------------- CANCELAR VENTA --------------------

@login_required
@user_passes_test(es_vendedor)
def cancelar_venta(request):
    """Cancela el proceso de venta actual y redirecciona al dashboard"""
    messages.info(request, "Venta cancelada. El carrito se ha vaciado.")
    return redirect('ventas:venta_dashboard')


# -------------------- HISTORIAL DE VENTAS --------------------

@login_required
@user_passes_test(es_vendedor)
def historial_ventas(request):
    """Muestra el historial de ventas con filtros opcionales"""
    
    # Inicializar formulario de búsqueda
    form = BusquedaVentasForm(request.GET or None)
    ventas = Venta.objects.filter(usuario=request.user)
    
    # Aplicar filtros si se proporcionan
    if form.is_valid():
        fecha_inicio = form.cleaned_data.get('fecha_inicio')
        fecha_fin = form.cleaned_data.get('fecha_fin')
        metodo_pago = form.cleaned_data.get('metodo_pago')
        
        if fecha_inicio:
            ventas = ventas.filter(fecha_hora__date__gte=fecha_inicio)
        
        if fecha_fin:
            ventas = ventas.filter(fecha_hora__date__lte=fecha_fin)
        
        if metodo_pago:
            ventas = ventas.filter(metodo_pago=metodo_pago)
    
    # Ordenar por fecha descendente
    ventas = ventas.order_by('-fecha_hora')
    
    context = {
        'ventas': ventas,
        'form': form
    }
    
    return render(request, 'historial_ventas.html', context)


# -------------------- DETALLE INDIVIDUAL DE VENTA --------------------

@login_required
@user_passes_test(es_vendedor)
def detalle_venta(request, venta_id):
    """Muestra los detalles de una venta específica"""
    
    venta = get_object_or_404(Venta, id=venta_id, usuario=request.user)
    detalles = venta.detalles.all()
    
    # Calcular totales
    subtotal = sum(detalle.precio_unitario * detalle.cantidad for detalle in detalles)
    descuentos = sum(detalle.descuento_aplicado * detalle.cantidad for detalle in detalles)
    
    context = {
        'venta': venta,
        'detalles': detalles,
        'subtotal': subtotal,
        'descuentos': descuentos,
        'total': venta.total
    }
    
    return render(request, 'detalle_venta.html', context)


# -------------------- CANCELAR UNA VENTA EXISTENTE --------------------

@login_required
@user_passes_test(es_vendedor)
def cancelar_venta_existente(request, venta_id):
    """Cancela una venta existente (cambia estado y revierte stock)"""
    
    venta = get_object_or_404(Venta, id=venta_id, usuario=request.user, estado='activa')
    
    try:
        # Intentar cancelar la venta
        if venta.cancelar():
            messages.success(request, f"Venta #{venta.id} cancelada correctamente. Stock restaurado.")
        else:
            messages.error(request, "No se pudo cancelar la venta.")
    
    except Exception as e:
        messages.error(request, f"Error al cancelar la venta: {str(e)}")
    
    return redirect('ventas:historial_ventas')


# -------------------- GENERAR TICKET PDF --------------------

@login_required
@user_passes_test(es_vendedor)
def generar_ticket_pdf(request, venta_id):
    """Genera un PDF con el ticket de venta"""
    
    venta = get_object_or_404