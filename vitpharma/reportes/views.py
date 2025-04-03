from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db.models import Sum
from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML
from datetime import datetime
import tempfile
import os
from django.conf import settings

from turnos.models import Turno
from ventas.models import Venta
from inventario.models import Producto, InventarioProducto, Proveedor
from authapp.models import PerfilUsuario
from reportes.models import LogReporteGenerado

# ========================= CONFIGURAR TEMPFILE PARA WINDOWS =========================
tempfile.tempdir = os.path.join(settings.BASE_DIR, 'tmp')

# ========================= PERMISOS =========================

def es_administrador(user):
    return user.is_authenticated and user.groups.filter(name="administrador").exists()

# ========================= DASHBOARD DE REPORTES =========================

@login_required
@user_passes_test(es_administrador)
def dashboard_reportes(request):
    return render(request, 'dashboard_reportes.html')


# ========================= REPORTE DE CAJAS GENERAL =========================

@login_required
@user_passes_test(es_administrador)
def reporte_cajas_general(request):
    turnos = Turno.objects.filter(estado='finalizado')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
            fecha_fin_dt = fecha_fin_dt.replace(hour=23, minute=59, second=59)
            turnos = turnos.filter(hora_inicio__range=(fecha_inicio_dt, fecha_fin_dt))

            LogReporteGenerado.objects.create(
                usuario=request.user,
                tipo_reporte='cajas_general',
                parametros=f"De {fecha_inicio} a {fecha_fin}"
            )
        except ValueError:
            pass

    contexto = {
        'turnos': turnos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }
    return render(request, 'reporte_cajas_general.html', contexto)


# ========================= HISTORIAL DE CORTES DE CAJA =========================

@login_required
@user_passes_test(es_administrador)
def historial_cortes_admin(request):
    cortes = Turno.objects.filter(estado='finalizado').order_by('-hora_inicio')

    LogReporteGenerado.objects.create(
        usuario=request.user,
        tipo_reporte='cortes_historial',
        parametros='Historial completo de cortes'
    )

    contexto = {
        'cortes': cortes,
    }
    return render(request, 'historial_cortes_admin.html', contexto)


# ========================= HISTORIAL DE VENTAS =========================

@login_required
@user_passes_test(es_administrador)
def historial_ventas_admin(request):
    ventas = Venta.objects.filter(estado='activa').order_by('-fecha_hora')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
            fecha_fin_dt = fecha_fin_dt.replace(hour=23, minute=59, second=59)
            ventas = ventas.filter(fecha_hora__range=(fecha_inicio_dt, fecha_fin_dt))

            LogReporteGenerado.objects.create(
                usuario=request.user,
                tipo_reporte='ventas_historial',
                parametros=f"De {fecha_inicio} a {fecha_fin}"
            )
        except ValueError:
            pass

    contexto = {
        'ventas': ventas,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }
    return render(request, 'historial_ventas_admin.html', contexto)


# ========================= REPORTE DE INVENTARIO =========================

@login_required
@user_passes_test(es_administrador)
def reporte_inventario_admin(request):
    productos = Producto.objects.prefetch_related('lotes').all()

    LogReporteGenerado.objects.create(
        usuario=request.user,
        tipo_reporte='inventario',
        parametros='Todos los productos y sus lotes'
    )

    contexto = {
        'productos': productos,
    }
    return render(request, 'reporte_inventario_admin.html', contexto)


# ========================= REPORTE DE PROVEEDORES =========================

@login_required
@user_passes_test(es_administrador)
def reporte_proveedores(request):
    proveedores = Proveedor.objects.all()

    LogReporteGenerado.objects.create(
        usuario=request.user,
        tipo_reporte='proveedores',
        parametros='Listado completo de proveedores'
    )

    contexto = {
        'proveedores': proveedores,
    }
    return render(request, 'reporte_proveedores.html', contexto)


# ========================= EXPORTACIONES PDF =========================

@login_required
@user_passes_test(es_administrador)
def exportar_reporte_cajas_pdf(request):
    turnos = Turno.objects.filter(estado='finalizado')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
            fecha_fin_dt = fecha_fin_dt.replace(hour=23, minute=59, second=59)
            turnos = turnos.filter(hora_inicio__range=(fecha_inicio_dt, fecha_fin_dt))
        except ValueError:
            pass

    html_string = render_to_string("reporte_cajas_general_pdf.html", {
        'turnos': turnos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_cajas_general.pdf"'

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as output:
        HTML(string=html_string).write_pdf(target=output.name)
        output.seek(0)
        response.write(output.read())

    return response


@login_required
@user_passes_test(es_administrador)
def exportar_cortes_admin_pdf(request):
    cortes = Turno.objects.filter(estado='finalizado').order_by('-hora_inicio')

    html_string = render_to_string("historial_cortes_admin_pdf.html", {
        'cortes': cortes,
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="historial_cortes_admin.pdf"'

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as output:
        HTML(string=html_string).write_pdf(target=output.name)
        output.seek(0)
        response.write(output.read())

    return response


@login_required
@user_passes_test(es_administrador)
def exportar_historial_ventas_pdf(request):
    ventas = Venta.objects.filter(estado='activa').order_by('-fecha_hora')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
            fecha_fin_dt = fecha_fin_dt.replace(hour=23, minute=59, second=59)
            ventas = ventas.filter(fecha_hora__range=(fecha_inicio_dt, fecha_fin_dt))
        except ValueError:
            pass

    html_string = render_to_string("historial_ventas_admin_pdf.html", {
        'ventas': ventas,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="historial_ventas_admin.pdf"'

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as output:
        HTML(string=html_string).write_pdf(target=output.name)
        output.seek(0)
        response.write(output.read())

    return response


@login_required
@user_passes_test(es_administrador)
def exportar_inventario_pdf(request):
    productos = Producto.objects.prefetch_related('lotes').all()

    html_string = render_to_string("reporte_inventario_admin_pdf.html", {
        'productos': productos,
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_inventario.pdf"'

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as output:
        HTML(string=html_string).write_pdf(target=output.name)
        output.seek(0)
        response.write(output.read())

    return response


@login_required
@user_passes_test(es_administrador)
def exportar_proveedores_pdf(request):
    proveedores = Proveedor.objects.all()

    html_string = render_to_string("reporte_proveedores_pdf.html", {
        'proveedores': proveedores,
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_proveedores.pdf"'

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as output:
        HTML(string=html_string).write_pdf(target=output.name)
        output.seek(0)
        response.write(output.read())

    return response
