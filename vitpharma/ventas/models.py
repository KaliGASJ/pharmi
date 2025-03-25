from django.db import models
from django.contrib.auth.models import User
from turnos.models import Turno
from inventario.models import Producto, InventarioProducto
from django.core.validators import MinValueValidator
from django.utils import timezone
import os


# -------------------- Ruta personalizada para guardar PDF del ticket --------------------

def ruta_ticket_pdf(instance, filename):
    nombre_archivo = f"venta_{instance.id}_{instance.usuario.username}.pdf"
    return os.path.join('tickets', nombre_archivo)


# -------------------- MÉTODOS DE PAGO --------------------

class MetodoPago(models.Model):
    nombre = models.CharField(max_length=40, unique=True)

    def __str__(self):
        return self.nombre


# -------------------- VENTA --------------------

class Venta(models.Model):
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('cancelada', 'Cancelada'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ventas')
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name='ventas')
    fecha_hora = models.DateTimeField(default=timezone.now)
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.SET_NULL, null=True)

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    con_cuanto_paga = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Solo se usa si el método de pago es en efectivo"
    )

    cambio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Cambio devuelto al cliente (solo efectivo)"
    )

    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activa')
    ticket_pdf = models.FileField(upload_to=ruta_ticket_pdf, blank=True, null=True)

    def __str__(self):
        return f"Venta #{self.id} - {self.usuario.username} - {self.metodo_pago}"

    def cancelar(self):
        self.estado = 'cancelada'
        self.save()

    def calcular_cambio(self):
        """
        Calcula el cambio solo si el método de pago es efectivo
        """
        if self.metodo_pago and "efectivo" in self.metodo_pago.nombre.lower():
            return max(self.con_cuanto_paga - self.total, 0)
        return 0.00


# -------------------- DETALLE DE VENTA --------------------

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    lote = models.ForeignKey(InventarioProducto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_aplicado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.producto.nombre} - {self.cantidad} unidad(es)"

    def calcular_subtotal(self):
        return (self.precio_unitario - self.descuento_aplicado) * self.cantidad
