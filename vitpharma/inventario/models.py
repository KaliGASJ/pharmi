from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


# -------------------- CATEGORÍAS Y DEPARTAMENTOS --------------------

class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True, null=False)

    def __str__(self):
        return self.nombre


class Departamento(models.Model):
    id_departamento = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True, null=False)

    def __str__(self):
        return self.nombre


# -------------------- PROVEEDORES --------------------

class Proveedor(models.Model):
    id_proveedor = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True, null=False)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.nombre


# -------------------- PRODUCTOS --------------------

class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, null=False)
    descripcion = models.TextField(blank=True, null=True)
    id_categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=False)
    id_departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE, null=False)
    stock_minimo = models.PositiveIntegerField(default=5, null=False)

    # Código de Barras (Obligatorio y único)
    codigo_barras = models.CharField(
        max_length=50,
        unique=True,
        null=False,
        validators=[RegexValidator(regex='^[0-9]*$', message="El código de barras solo puede contener números.")]
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True, null=False)
    usuario_registro = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="registro_producto")
    usuario_modificacion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="modificacion_producto")
    fecha_modificacion = models.DateTimeField(auto_now=True, null=False)

    def __str__(self):
        return f"{self.nombre} - Código: {self.codigo_barras}"

    def total_stock(self):
        """Calcula el stock total sumando los lotes disponibles."""
        return sum(lote.cantidad for lote in self.lotes.all())

    def en_bajo_stock(self):
        """Determina si el producto está en stock bajo."""
        return self.total_stock() <= self.stock_minimo

    def actualizar_stock_total(self):
        """Recalcula el stock total y lo guarda en la base de datos."""
        self.save()


# -------------------- INVENTARIO PRODUCTOS (LOTES) --------------------

class InventarioProducto(models.Model):
    id_inventario = models.AutoField(primary_key=True)
    producto = models.ForeignKey(Producto, related_name="lotes", on_delete=models.CASCADE, null=False)
    lote = models.CharField(max_length=50, default="SIN-LOTE", null=False)
    id_proveedor = models.ForeignKey(Proveedor, related_name="productos_proveedor", on_delete=models.SET_NULL, null=True)
    fecha_caducidad = models.DateField(blank=True, null=True)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    cantidad = models.PositiveIntegerField(default=0, null=False)
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, default=0.00)
    usuario_registro = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="registro_stock")
    usuario_modificacion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="modificacion_stock")
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=False)
    fecha_modificacion = models.DateTimeField(auto_now=True, null=False)

    def __str__(self):
        return f"{self.producto.nombre} - Lote: {self.lote} - Cantidad: {self.cantidad}"

    def save(self, *args, **kwargs):
        """Al guardar, evita precios negativos y actualiza el stock del producto."""
        if self.precio_compra < 0 or self.precio_venta < 0:
            raise ValueError("El precio de compra y venta no pueden ser negativos.")

        if self.precio_venta < self.precio_compra:
            raise ValueError("El precio de venta no puede ser menor al precio de compra.")

        super().save(*args, **kwargs)
        self.producto.actualizar_stock_total()

    def eliminar_lote(self):
        """Reduce el stock total del producto al eliminar un lote."""
        self.producto.actualizar_stock_total()
        self.delete()
