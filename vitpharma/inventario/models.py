from django.db import models 
from django.contrib.auth.models import User
from datetime import date
from django.core.validators import RegexValidator

# -------------------- CATEGORÍAS Y DEPARTAMENTOS --------------------

class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class Departamento(models.Model):
    id_departamento = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

# -------------------- PROVEEDORES --------------------

class Proveedor(models.Model):
    id_proveedor = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.nombre

# -------------------- PRODUCTOS --------------------

class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    id_categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    id_departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)
    estado = models.BooleanField(default=False)  # Por defecto inactivo
    stock_minimo = models.PositiveIntegerField(default=5)  # Mínimo antes de alerta
    codigo_barras = models.CharField(
        max_length=50, 
        unique=True, 
        blank=True, 
        null=True, 
        validators=[RegexValidator(regex='^[0-9]*$', message="El código de barras solo puede contener números.")]
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usuario_registro = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="registro_producto")
    usuario_modificacion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="modificacion_producto")
    fecha_modificacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

    def total_stock(self):
        """Calcula el stock total sumando los lotes disponibles"""
        return sum(lote.cantidad for lote in self.lotes.all() if lote.cantidad > 0)

    def actualizar_estado(self):
        """Cambia el estado del producto a activo/inactivo dependiendo del stock."""
        self.estado = self.total_stock() > 0
        self.save()

    def en_bajo_stock(self):
        """Determina si el producto está en stock bajo considerando el total de sus lotes"""
        return self.total_stock() <= self.stock_minimo

# -------------------- INVENTARIO PRODUCTOS (LOTES) --------------------

class InventarioProducto(models.Model):
    id_inventario = models.AutoField(primary_key=True)
    producto = models.ForeignKey(Producto, related_name="lotes", on_delete=models.CASCADE)
    lote = models.CharField(max_length=50, blank=True, null=True)
    id_proveedor = models.ForeignKey(Proveedor, related_name="productos_proveedor", on_delete=models.SET_NULL, blank=True, null=True)
    fecha_caducidad = models.DateField(blank=True, null=True)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.PositiveIntegerField(default=0)  # Stock disponible por lote
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, default=0.00)
    usuario_registro = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="registro_stock")
    usuario_modificacion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="modificacion_stock")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.producto.nombre} - Lote: {self.lote if self.lote else 'N/A'} - Cantidad: {self.cantidad}"

    def save(self, *args, **kwargs):
        """Al guardar, actualiza el estado del producto."""
        super().save(*args, **kwargs)
        self.producto.actualizar_estado()

    def proximo_a_caducar(self, dias=60):
        """Determina si este lote está próximo a caducar en los próximos X días"""
        if self.fecha_caducidad and self.fecha_caducidad > date.today():
            return (self.fecha_caducidad - date.today()).days <= dias
        return False
