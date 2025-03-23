from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from inventario.models import Producto, InventarioProducto

# ---------------------- VERIFICACIÓN DE ROL VENDEDOR ----------------------

def es_vendedor(user):
    return user.is_authenticated and user.groups.filter(name='vendedor').exists()

# ----------------------------- DASHBOARD INVENTARIO -----------------------------

@login_required
@user_passes_test(es_vendedor)
def inventario_vendedor_dashboard(request):
    query = request.GET.get('q', '')  # por defecto cadena vacía
    productos = Producto.objects.all().order_by('nombre')

    if query:
        productos = productos.filter(
            Q(nombre__icontains=query) |
            Q(codigo_barras__icontains=query)
        )

    return render(request, 'inventario_vendedor_dashboard.html', {
        'productos': productos,
        'query': query
    })

