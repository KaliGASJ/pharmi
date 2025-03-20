from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Producto, InventarioProducto, Proveedor
from .forms import ProductoForm, AgregarLoteForm, AgregarStockForm, EditarLoteForm, EliminarLoteForm


# -------------------- PERMISOS --------------------

def es_administrador(user):
    return user.is_authenticated and user.groups.filter(name="administrador").exists()

def es_vendedor(user):
    return user.is_authenticated and user.groups.filter(name="vendedor").exists()


# -------------------- LISTAR PRODUCTOS --------------------

@login_required
def listar_productos(request):
    productos = Producto.objects.all()
    return render(request, "listar_productos.html", {"productos": productos})


# -------------------- DETALLE DEL PRODUCTO --------------------

@login_required
def detalle_producto(request, producto_id):
    """Muestra todos los detalles del producto."""
    producto = get_object_or_404(Producto, id_producto=producto_id)
    return render(request, "detalle_producto.html", {"producto": producto})


# -------------------- DETALLE DE LOTES --------------------

@login_required
def detalle_lotes(request, producto_id):
    """Muestra todos los lotes de un producto específico."""
    producto = get_object_or_404(Producto, id_producto=producto_id)
    lotes = InventarioProducto.objects.filter(producto=producto)
    return render(request, "detalle_lotes.html", {"producto": producto, "lotes": lotes})


# -------------------- ADMINISTRADOR: GESTIÓN DE PRODUCTOS --------------------

@login_required
@user_passes_test(es_administrador)
def agregar_producto(request):
    if request.method == "POST":
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.usuario_registro = request.user
            producto.save()
            messages.success(request, f"Producto '{producto.nombre}' agregado correctamente.")
            return redirect("inventario:listar_productos")
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
            return redirect("inventario:listar_productos")
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
@user_passes_test(es_administrador)
def agregar_lote(request, producto_id):
    producto = get_object_or_404(Producto, id_producto=producto_id)

    if request.method == "POST":
        form = AgregarLoteForm(request.POST)
        if form.is_valid():
            lote = form.save(commit=False)
            lote.producto = producto  # Asociar el lote con el producto
            lote.usuario_registro = request.user
            lote.save()
            messages.success(request, f"Lote '{lote.lote}' agregado correctamente.")
            return redirect("inventario:detalle_lotes", producto_id=producto.id_producto)
        messages.error(request, "Error al agregar el lote. Verifique los datos.")
    else:
        form = AgregarLoteForm()

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
                messages.success(request, f"Stock del lote '{stock.lote}' actualizado correctamente.")
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
            lote = form.save(commit=False)
            lote.usuario_modificacion = request.user
            lote.save()
            messages.success(request, f"Lote '{lote.lote}' actualizado correctamente.")
            return redirect("inventario:detalle_lotes", producto_id=lote.producto.id_producto)
        messages.error(request, "Error al editar el lote. Verifique los datos.")
    else:
        form = EditarLoteForm(instance=lote)

    return render(request, "editar_lote.html", {"form": form, "lote": lote})


# -------------------- ADMINISTRADOR: ELIMINAR LOTE --------------------

@login_required
@user_passes_test(es_administrador)
def eliminar_lote(request, lote_id):
    lote = get_object_or_404(InventarioProducto, id_inventario=lote_id)
    producto = lote.producto

    if request.method == "POST":
        lote.delete()
        messages.success(request, f"Lote '{lote.lote}' eliminado correctamente.")
        return redirect("inventario:detalle_lotes", producto_id=producto.id_producto)

    return render(request, "eliminar_lote.html", {"lote": lote, "producto": producto})
