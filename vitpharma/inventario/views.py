from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Producto, InventarioProducto, Proveedor
from .forms import ProductoForm, InventarioProductoForm, AgregarStockForm

# -------------------- PERMISOS --------------------

def es_administrador(user):
    """Verifica si el usuario es administrador."""
    return user.is_authenticated and user.groups.filter(name="administrador").exists()

def es_vendedor(user):
    """Verifica si el usuario es vendedor."""
    return user.is_authenticated and user.groups.filter(name="vendedor").exists()

# -------------------- LISTAR PRODUCTOS --------------------

@login_required
def listar_productos(request):
    """Lista todos los productos en el inventario."""
    productos = Producto.objects.all()
    return render(request, "listar_productos.html", {"productos": productos})

# -------------------- ADMINISTRADOR: GESTIÓN DE PRODUCTOS --------------------

@login_required
@user_passes_test(es_administrador)
def agregar_producto(request):
    """Permite al administrador agregar un nuevo producto."""
    if request.method == "POST":
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.usuario_registro = request.user
            producto.save()
            messages.success(request, f"Producto '{producto.nombre}' agregado correctamente.")
            return redirect("inventario:listar_productos")
        else:
            messages.error(request, "Error al agregar el producto. Verifique los datos.")
    else:
        form = ProductoForm()

    return render(request, "agregar_producto.html", {"form": form})

@login_required
@user_passes_test(es_administrador)
def editar_producto(request, producto_id):
    """Permite al administrador editar un producto existente (NO modifica stock)."""
    producto = get_object_or_404(Producto, id_producto=producto_id)

    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.usuario_modificacion = request.user
            producto.save()
            messages.success(request, f"Producto '{producto.nombre}' actualizado correctamente.")
            return redirect("inventario:listar_productos")
        else:
            messages.error(request, "Error al actualizar el producto. Verifique los datos.")
    else:
        form = ProductoForm(instance=producto)

    return render(request, "editar_producto.html", {"form": form, "producto": producto})

@login_required
@user_passes_test(es_administrador)
def eliminar_producto(request, producto_id):
    """Permite al administrador eliminar un producto del inventario."""
    producto = get_object_or_404(Producto, id_producto=producto_id)
    
    if InventarioProducto.objects.filter(producto=producto).exists():
        messages.error(request, "No se puede eliminar un producto con stock disponible.")
        return redirect("inventario:listar_productos")

    if request.method == "POST":
        producto.delete()
        messages.success(request, f"Producto '{producto.nombre}' eliminado correctamente.")
        return redirect("inventario:listar_productos")

    return render(request, "eliminar_producto.html", {"producto": producto})

# -------------------- VENDEDORES: AGREGAR STOCK --------------------

@login_required
@user_passes_test(es_vendedor)
def agregar_stock(request):
    """Permite a los vendedores agregar stock a un producto existente."""
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
                lote_existente.usuario_modificacion = request.user
                lote_existente.save()
                messages.success(request, f"Stock del lote '{stock.lote}' actualizado correctamente.")
            else:
                stock.save()
                messages.success(request, f"Nuevo lote agregado para '{stock.producto.nombre}'.")

            return redirect("inventario:listar_productos")
        else:
            messages.error(request, "Error al agregar stock. Verifique los datos ingresados.")
    else:
        form = AgregarStockForm()

    return render(request, "agregar_stock.html", {"form": form})

# -------------------- ADMINISTRADOR: GESTIÓN DE LOTES --------------------

@login_required
@user_passes_test(es_administrador)
def gestionar_stock(request, producto_id):
    """Permite al administrador gestionar los lotes y el stock de un producto."""
    producto = get_object_or_404(Producto, id_producto=producto_id)
    lotes = InventarioProducto.objects.filter(producto=producto)
    proveedores = Proveedor.objects.all()  # Obtener la lista de proveedores

    if request.method == "POST":
        form = InventarioProductoForm(request.POST)
        if form.is_valid():
            lote = form.save(commit=False)
            lote.producto = producto
            lote.usuario_modificacion = request.user

            lote_existente = InventarioProducto.objects.filter(
                producto=producto, 
                lote=lote.lote,
                id_proveedor=lote.id_proveedor
            ).first()

            if lote_existente:
                lote_existente.cantidad += lote.cantidad
                lote_existente.usuario_modificacion = request.user
                lote_existente.save()
                messages.success(request, f"Stock del lote '{lote.lote}' actualizado correctamente.")
            else:
                lote.save()
                messages.success(request, f"Nuevo lote agregado para '{producto.nombre}'.")

            return redirect("inventario:gestionar_stock", producto_id=producto.id_producto)
        else:
            # 🔴 Imprimir errores en la consola del servidor
            print("Errores del formulario:", form.errors)
            messages.error(request, "Error al actualizar stock. Verifique los datos.")
    else:
        form = InventarioProductoForm(initial={"producto": producto})

    return render(request, "gestionar_stock.html", {
        "form": form, 
        "producto": producto, 
        "lotes": lotes,
        "proveedores": proveedores  # Pasar proveedores al contexto
    })

# -------------------- ADMINISTRADOR: HISTORIAL DE MODIFICACIONES --------------------

@login_required
@user_passes_test(es_administrador)
def historial_modificaciones(request):
    """Muestra el historial de modificaciones de inventario."""
    historial = InventarioProducto.objects.all().order_by("-fecha_modificacion")
    return render(request, "historial_modificaciones.html", {"historial": historial})
