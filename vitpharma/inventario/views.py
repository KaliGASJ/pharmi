from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Producto, InventarioProducto, Proveedor
from .forms import (
    ProductoForm, AgregarLoteForm, AgregarStockForm, EditarLoteForm,
    EliminarLoteForm, AgregarProveedorForm, EditarProveedorForm, EliminarProveedorForm
)
from datetime import date
from django.db.models import Q
from django.http import HttpResponse


# -------------------- PERMISOS --------------------

def es_administrador(user):
    return user.is_authenticated and user.groups.filter(name="administrador").exists()

def es_vendedor(user):
    return user.is_authenticated and user.groups.filter(name="vendedor").exists()


# -------------------- UTILIDAD --------------------

def volver_atras():
    return HttpResponse("<script>history.back();</script>")


# -------------------- LISTAR PRODUCTOS --------------------

@login_required
def listar_productos(request):
    productos = Producto.objects.all()
    return render(request, "listar_productos.html", {"productos": productos})


# -------------------- DETALLE DEL PRODUCTO --------------------

@login_required
def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto, id_producto=producto_id)
    return render(request, "detalle_producto.html", {"producto": producto})


# -------------------- DETALLE DE LOTES --------------------

@login_required
def detalle_lotes(request, producto_id):
    producto = get_object_or_404(Producto, id_producto=producto_id)
    lotes = InventarioProducto.objects.filter(producto=producto)
    return render(request, "detalle_lotes.html", {"producto": producto, "lotes": lotes})


# -------------------- ADMINISTRADOR: GESTIÓN DE PRODUCTOS --------------------

@login_required
def agregar_producto(request):
    if request.method == "POST":
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.usuario_registro = request.user
            producto.save()
            messages.success(request, f"Producto '{producto.nombre}' agregado correctamente.")
            grupo = request.user.groups.first().name.lower() if request.user.groups.exists() else None
            if grupo == "administrador":
                return redirect("inventario:listar_productos")
            elif grupo == "vendedor":
                return redirect("inventariovendedor:inventario_vendedor_dashboard")
            return redirect("home")
        messages.error(request, "Error al agregar el producto. Verifique los datos.")
    else:
        form = ProductoForm()
    return render(request, "agregar_producto.html", {"form": form})


@login_required
@user_passes_test(es_administrador)
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id_producto=producto_id)
    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.usuario_modificacion = request.user
            producto.save()
            messages.success(request, f"Producto '{producto.nombre}' actualizado correctamente.")
            return volver_atras()
        messages.error(request, "Error al actualizar el producto. Verifique los datos.")
    else:
        form = ProductoForm(instance=producto)
    return render(request, "editar_producto.html", {"form": form, "producto": producto})


@login_required
@user_passes_test(es_administrador)
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id_producto=producto_id)
    if InventarioProducto.objects.filter(producto=producto).exists():
        messages.error(request, "No se puede eliminar un producto con stock disponible.")
        return redirect("inventario:listar_productos")
    if request.method == "POST":
        producto.delete()
        messages.success(request, f"Producto '{producto.nombre}' eliminado correctamente.")
        return redirect("inventario:listar_productos")
    return render(request, "eliminar_producto.html", {"producto": producto})


# -------------------- ADMINISTRADOR: AGREGAR LOTE --------------------

@login_required
def agregar_lote(request, producto_id):
    producto = get_object_or_404(Producto, id_producto=producto_id)
    if request.method == "POST":
        form = AgregarLoteForm(request.POST, producto_fijo=producto)
        if form.is_valid():
            lote = form.save(commit=False)
            lote.producto = producto
            lote.usuario_registro = request.user
            lote.save()
            messages.success(request, f"Lote '{lote.codigo_lote}' agregado a '{producto.nombre}'.")
            return redirect("inventario:detalle_lotes", producto_id=producto.id_producto)
        messages.error(request, "❌ Error al agregar el lote. Verifique los datos.")
    else:
        form = AgregarLoteForm(producto_fijo=producto)
    return render(request, "agregar_lote.html", {"form": form, "producto": producto})


# -------------------- VENDEDORES: AGREGAR STOCK --------------------

@login_required
@user_passes_test(es_vendedor)
def agregar_stock(request):
    if request.method == "POST":
        form = AgregarStockForm(request.POST)
        if form.is_valid():
            stock = form.save(commit=False)
            stock.usuario_registro = request.user
            lote_existente = InventarioProducto.objects.filter(
                producto=stock.producto,
                lote=stock.lote,
                id_proveedor=stock.id_proveedor
            ).first()
            if lote_existente:
                lote_existente.cantidad += stock.cantidad
                lote_existente.save()
                messages.success(request, f"Stock actualizado para '{lote_existente.codigo_lote}'.")
            else:
                messages.error(request, "Solo se permite agregar stock a lotes existentes.")
            return redirect("inventario:detalle_lotes", producto_id=stock.producto.id_producto)
        messages.error(request, "Error al agregar stock. Verifique los datos.")
    else:
        form = AgregarStockForm()
    return render(request, "agregar_stock.html", {"form": form})


# -------------------- ADMINISTRADOR: EDITAR LOTE --------------------

@login_required
@user_passes_test(es_administrador)
def editar_lote(request, lote_id):
    lote = get_object_or_404(InventarioProducto, id_inventario=lote_id)

    if request.method == "POST":
        form = EditarLoteForm(request.POST, instance=lote)
        if form.is_valid():
            lote_actualizado = form.save(commit=False)
            lote_actualizado.usuario_modificacion = request.user
            lote_actualizado.save()
            messages.success(request, f"Lote '{lote_actualizado.codigo_lote}' actualizado correctamente.")
            return redirect("inventario:detalle_lotes", producto_id=lote_actualizado.producto.id_producto)
        else:
            messages.error(request, "❌ Error al editar el lote. Verifique los datos.")
    else:
        form = EditarLoteForm(instance=lote)

    return render(request, "editar_lote.html", {
        "form": form,
        "lote": lote
    })



# -------------------- ADMINISTRADOR: ELIMINAR LOTE --------------------

@login_required
@user_passes_test(es_administrador)
def eliminar_lote(request, lote_id):
    lote = get_object_or_404(InventarioProducto, id_inventario=lote_id)
    producto = lote.producto
    if request.method == "POST":
        lote.delete()
        messages.success(request, f"Lote '{lote.codigo_lote}' eliminado.")
        return redirect("inventario:detalle_lotes", producto_id=producto.id_producto)
    return render(request, "eliminar_lote.html", {"lote": lote, "producto": producto})


# -------------------- NUEVAS VISTAS --------------------

@login_required
def productos_bajo_stock(request):
    productos = Producto.objects.all()
    productos_bajo_stock = sorted(
        [p for p in productos if p.en_bajo_stock()],
        key=lambda x: x.total_stock()
    )
    return render(request, "productos_bajo_stock.html", {"productos": productos_bajo_stock})


@login_required
def lotes_proximos_caducar(request):
    hoy = date.today()
    query = request.GET.get("q", "").strip()
    lotes = InventarioProducto.objects.exclude(fecha_caducidad=None).filter(fecha_caducidad__gte=hoy)
    if query:
        lotes = lotes.filter(
            Q(producto__nombre__icontains=query) |
            Q(producto__codigo_barras__icontains=query) |
            Q(lote__icontains=query) |
            Q(codigo_lote__icontains=query)
        )

    lotes_coloreados = []
    for lote in lotes:
        dias = (lote.fecha_caducidad - hoy).days
        lote.dias_restantes = dias
        if dias <= 60:
            lote.alerta = "rojo"
        elif dias <= 180:
            lote.alerta = "amarillo"
        else:
            lote.alerta = "verde"
        lotes_coloreados.append(lote)

    lotes_ordenados = sorted(lotes_coloreados, key=lambda x: x.dias_restantes)

    return render(request, "lotes_proximos_caducar.html", {
        "lotes": lotes_ordenados,
        "hoy": hoy,
        "query": query
    })


# -------------------- GESTIÓN DE PROVEEDORES --------------------

@login_required
@user_passes_test(es_administrador)
def listar_proveedores(request):
    proveedores = Proveedor.objects.all()
    return render(request, "listar_proveedores.html", {"proveedores": proveedores})


@login_required
@user_passes_test(es_administrador)
def agregar_proveedor(request):
    if request.method == "POST":
        form = AgregarProveedorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Proveedor registrado correctamente.")
            return redirect("inventario:listar_proveedores")
        messages.error(request, "Error al registrar el proveedor.")
    else:
        form = AgregarProveedorForm()
    return render(request, "agregar_proveedor.html", {"form": form})


@login_required
@user_passes_test(es_administrador)
def editar_proveedor(request, proveedor_id):
    proveedor = get_object_or_404(Proveedor, id_proveedor=proveedor_id)
    if request.method == "POST":
        form = EditarProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, "Proveedor actualizado correctamente.")
            return redirect("inventario:listar_proveedores")
        messages.error(request, "Error al actualizar el proveedor.")
    else:
        form = EditarProveedorForm(instance=proveedor)
    return render(request, "editar_proveedor.html", {"form": form, "proveedor": proveedor})


@login_required
@user_passes_test(es_administrador)
def eliminar_proveedor(request, proveedor_id):
    proveedor = get_object_or_404(Proveedor, id_proveedor=proveedor_id)
    if request.method == "POST":
        form = EliminarProveedorForm(request.POST)
        if form.is_valid() and form.cleaned_data["confirmacion"]:
            proveedor.delete()
            messages.success(request, "Proveedor eliminado correctamente.")
            return redirect("inventario:listar_proveedores")
    else:
        form = EliminarProveedorForm()
    return render(request, "eliminar_proveedor.html", {"form": form, "proveedor": proveedor})
