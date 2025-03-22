from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from datetime import date


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

    codigo_barras = models.CharField(
        max_length=20,
        unique=True,
        null=False,
        validators=[RegexValidator(regex='^[0-9]*$', message="El código de barras solo puede contener números.")]
    )

    estado = models.CharField(
        max_length=10,
        choices=[("activo", "Activo"), ("inactivo", "Inactivo")],
        default="inactivo"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True, null=False)
    usuario_registro = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="registro_producto")
    usuario_modificacion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="modificacion_producto")
    fecha_modificacion = models.DateTimeField(auto_now=True, null=False)

    def __str__(self):
        return f"{self.nombre} (CB: {self.codigo_barras})"

    def total_stock(self):
        return sum(lote.cantidad for lote in self.lotes.all())

    def en_bajo_stock(self):
        return self.total_stock() <= self.stock_minimo

    def actualizar_stock_total(self):
        stock_actual = self.total_stock()
        nuevo_estado = "activo" if stock_actual > 0 else "inactivo"
        if self.estado != nuevo_estado:
            self.estado = nuevo_estado
            self.save(update_fields=["estado"])


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

    def clean(self):
        if self.precio_compra < 0 or self.precio_venta < 0:
            raise ValidationError("El precio de compra y venta no pueden ser negativos.")
        if self.precio_venta < self.precio_compra:
            raise ValidationError("El precio de venta no puede ser menor al precio de compra.")
        if self.fecha_caducidad and self.fecha_caducidad < date.today():
            raise ValidationError("La fecha de caducidad no puede ser anterior a hoy.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Valida antes de guardar
        super().save(*args, **kwargs)
        self.producto.actualizar_stock_total()

    def eliminar_lote(self):
        self.delete()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.producto.actualizar_stock_total()

    def dias_para_caducar(self):
        if self.fecha_caducidad:
            return (self.fecha_caducidad - date.today()).days
        return None
