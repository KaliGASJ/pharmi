from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.urls import reverse
from django.db.models import Sum, Count
import json

from .models import Venta, DetalleVenta, MetodoPago
from turnos.models import Turno
from inventario.models import Producto, InventarioProducto
from .forms import VentaForm, DetalleVentaFormSet, MetodoPagoForm

def es_vendedor(user):
    return user.is_authenticated and user.groups.filter(name='vendedor').exists()

@login_required
@user_passes_test(es_vendedor)
def registro_venta(request):
    """Vista principal para el registro de ventas"""
    # Verificar si hay un turno activo
    turno_activo = Turno.objects.filter(
        usuario=request.user, 
        esta_activo=True
    ).first()
    
    if not turno_activo:
        messages.error(
            request, 
            "Debes iniciar un turno antes de registrar ventas"
        )
        return redirect('turnos:turno_vendedor')
    
    # Obtener productos disponibles para venta (con stock > 0)
    productos_disponibles = Producto.objects.filter(estado='activo')
    
    # Obtener métodos de pago disponibles
    metodos_pago = MetodoPago.objects.all()
    
    # Obtener estadísticas de ventas del turno actual
    ventas_turno = turno_activo.ventas.all()
    total_ventas = ventas_turno.aggregate(total=Sum('total'))['total'] or 0
    cantidad_ventas = ventas_turno.count()
    
    context = {
        'turno_activo': turno_activo,
        'productos': productos_disponibles,
        'metodos_pago': metodos_pago,
        'total_ventas': total_ventas,
        'cantidad_ventas': cantidad_ventas
    }
    
    return render(request, 'registro_venta.html', context)

@login_required
@user_passes_test(es_vendedor)
def buscar_productos(request):
    """Búsqueda de productos para la venta"""
    query = request.GET.get('q', '')
    
    if not query:
        return JsonResponse({'productos': []})
    
    # Buscar productos que coincidan con el nombre o código de barras
    productos = Producto.objects.filter(
        estado='activo'
    ).filter(
        nombre__icontains=query
    ) | Producto.objects.filter(
        estado='activo',
        codigo_barras__icontains=query
    )
    
    # Formatear datos para JSON
    resultado = []
    for producto in productos[:10]:  # Limitar a 10 resultados para mejor rendimiento
        # Obtener lotes disponibles con stock
        lotes = InventarioProducto.objects.filter(
            producto=producto,
            cantidad__gt=0
        ).order_by('fecha_caducidad')
        
        # Solo incluir si hay lotes disponibles
        if lotes.exists():
            resultado.append({
                'id': producto.id_producto,
                'nombre': producto.nombre,
                'codigo': producto.codigo_barras,
                'categoria': producto.id_categoria.nombre,
                'lotes': [
                    {
                        'id': lote.id_inventario,
                        'lote': lote.lote,
                        'stock': lote.cantidad,
                        'precio': float(lote.precio_venta),
                        'descuento': float(lote.descuento_porcentaje or 0),
                        'caducidad': lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else 'N/A'
                    } 
                    for lote in lotes
                ]
            })
    
    return JsonResponse({'productos': resultado})

@login_required
@user_passes_test(es_vendedor)
def procesar_venta(request):
    """Procesa la venta completa"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    # Verificar turno activo
    turno_activo = Turno.objects.filter(
        usuario=request.user, 
        esta_activo=True
    ).first()
    
    if not turno_activo:
        return JsonResponse({'error': 'No hay un turno activo'}, status=400)
    
    try:
        # Obtener datos de la venta del POST
        metodo_pago_id = request.POST.get('metodo_pago')
        items_json = request.POST.get('items', '[]')
        
        try:
            items = json.loads(items_json)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Formato de ítems inválido'}, status=400)
        
        if not metodo_pago_id or not items:
            return JsonResponse({'error': 'Datos incompletos'}, status=400)
        
        metodo_pago = get_object_or_404(MetodoPago, id=metodo_pago_id)
        
        # Procesar la venta dentro de una transacción
        with transaction.atomic():
            # Crear la venta
            venta = Venta(
                usuario=request.user,
                usuario_registro=request.user,
                turno=turno_activo,
                metodo_pago=metodo_pago,
                total=0  # Se actualizará después
            )
            venta.save()
            
            # Procesar cada ítem y crear los detalles
            total_venta = 0
            for item_data in items:
                lote_id = item_data.get('lote_id')
                cantidad = int(item_data.get('cantidad', 0))
                
                if not lote_id or cantidad <= 0:
                    continue
                
                # Obtener el lote
                lote = get_object_or_404(InventarioProducto, id_inventario=lote_id)
                
                # Verificar stock
                if lote.cantidad < cantidad:
                    raise ValueError(f"Stock insuficiente para {lote.producto.nombre}")
                
                # Calcular precio y descuento
                precio_unitario = lote.precio_venta
                descuento_unitario = (lote.precio_venta * lote.descuento_porcentaje / 100) if lote.descuento_porcentaje else 0
                
                # Crear detalle de venta
                detalle = DetalleVenta(
                    venta=venta,
                    lote_vendido=lote,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    descuento_unitario=descuento_unitario
                )
                detalle.calcular_subtotal()
                detalle.save()
                
                # Actualizar stock
                lote.cantidad -= cantidad
                lote.save()
                
                # Actualizar el estado del producto si es necesario
                lote.producto.actualizar_stock_total()
                
                # Sumar al total
                total_venta += detalle.subtotal
            
            # Actualizar total de la venta
            venta.total = total_venta
            venta.save(update_fields=['total'])
            
            # Generar ticket
            venta.generar_ticket_pdf()
            
            return JsonResponse({
                'success': True,
                'venta_id': venta.id,
                'total': float(venta.total),
                'ticket_url': venta.archivo_ticket.url if venta.archivo_ticket else None
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@user_passes_test(es_vendedor)
def historial_ventas(request):
    """Muestra el historial de ventas del vendedor"""
    # Obtener ventas del usuario
    ventas = Venta.objects.filter(usuario=request.user).order_by('-fecha_hora')
    
    # Filtrar por fecha si se proporciona
    fecha = request.GET.get('fecha')
    if fecha:
        try:
            fecha_obj = timezone.datetime.strptime(fecha, '%Y-%m-%d').date()
            ventas = ventas.filter(fecha_hora__date=fecha_obj)
        except ValueError:
            messages.warning(request, "Formato de fecha inválido")
    
    # Calcular totales para mostrar en la vista
    total_monto = ventas.aggregate(Sum('total'))['total__sum'] or 0
    promedio_venta = total_monto / ventas.count() if ventas.count() > 0 else 0
    
    return render(request, 'historial_ventas.html', {
        'ventas': ventas,
        'fecha': fecha,
        'total_monto': total_monto,
        'promedio_venta': promedio_venta
    })

@login_required
@user_passes_test(es_vendedor)
def detalle_venta(request, venta_id):
    """Muestra el detalle de una venta específica"""
    venta = get_object_or_404(Venta, id=venta_id, usuario=request.user)
    detalles = venta.detalles.all()
    
    # Calcular totales
    total_productos = detalles.aggregate(total=Sum('cantidad'))['total'] or 0
    total_descuento = detalles.aggregate(total=Sum('total_descuento'))['total'] or 0
    
    return render(request, 'detalle_venta.html', {
        'venta': venta,
        'detalles': detalles,
        'total_productos': total_productos,
        'total_descuento': total_descuento
    })

@login_required
@user_passes_test(es_vendedor)
def descargar_ticket(request, venta_id):
    """Permite descargar el ticket de una venta"""
    venta = get_object_or_404(Venta, id=venta_id, usuario=request.user)
    
    if not venta.archivo_ticket:
        messages.error(request, "Esta venta no tiene un ticket generado.")
        return redirect('ventas:historial_ventas')
    
    response = HttpResponse(venta.archivo_ticket.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_venta_{venta_id}.pdf"'
    return response

@login_required
@user_passes_test(es_vendedor)
def metodos_pago(request):
    """Gestiona los métodos de pago (solo para administradores)"""
    # Nota: Normalmente esto sería restringido a administradores
    metodos = MetodoPago.objects.all().order_by('nombre')
    
    if request.method == 'POST':
        form = MetodoPagoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Método de pago guardado correctamente")
            return redirect('ventas:metodos_pago')
    else:
        form = MetodoPagoForm()
    
    return render(request, 'metodos_pago.html', {
        'metodos': metodos,
        'form': form
    })

@login_required
@user_passes_test(es_vendedor)
def cancelar_venta(request, venta_id):
    """Permitiría cancelar una venta reciente (funcionalidad futura)"""
    venta = get_object_or_404(Venta, id=venta_id, usuario=request.user)
    
    # Verificar si la venta es reciente (menos de 1 hora)
    tiempo_transcurrido = timezone.now() - venta.fecha_hora
    if tiempo_transcurrido.total_seconds() > 3600:  # 1 hora en segundos
        messages.error(request, "No se pueden cancelar ventas con más de una hora de antigüedad")
        return redirect('ventas:detalle_venta', venta_id=venta_id)
        
    # Por ahora, simplemente mostrar la vista de confirmación
    # En una implementación real, se agregaría la lógica para revertir el inventario
    
    return render(request, 'confirmar_cancelar_venta.html', {
        'venta': venta
    })