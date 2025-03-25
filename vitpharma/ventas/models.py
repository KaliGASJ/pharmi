from django.db import models
from django.contrib.auth.models import User
from turnos.models import Turno
from inventario.models import Producto, InventarioProducto
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from decimal import Decimal
import os

# -------------------- Ruta personalizada para guardar PDF del ticket --------------------

def ruta_ticket_pdf(instance, filename):
    nombre_archivo = f"venta_{instance.id}_{instance.usuario.username}.pdf"
    return os.path.join('tickets', nombre_archivo)


# -------------------- MÉTODOS DE PAGO --------------------

class MetodoPago(models.Model):
    nombre = models.CharField(max_length=40, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
    fecha_modificacion = models.DateTimeField(auto_now=True, null=True)
    
    class Meta:
        verbose_name = "Método de pago"
        verbose_name_plural = "Métodos de pago"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre
    
    @property
    def es_efectivo(self):
        """
        Determina si este método de pago es efectivo
        """
        return 'efectivo' in self.nombre.lower()


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
    
    # Campos para auditoría
    usuario_registro = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='registro_ventas')
    usuario_modificacion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='modificacion_ventas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha_hora']
    
    def __str__(self):
        return f"Venta #{self.id} - {self.usuario.username} - {self.metodo_pago}"
    
    def save(self, *args, **kwargs):
        """
        Sobreescribe el método save para manejar el cambio automáticamente
        """
        # Solo para ventas nuevas (sin ID aún)
        if not self.id and self.metodo_pago and self.metodo_pago.es_efectivo and self.con_cuanto_paga:
            self.cambio = self.calcular_cambio()
        
        super().save(*args, **kwargs)
    
    def calcular_cambio(self):
        """
        Calcula el cambio solo si el método de pago es efectivo
        """
        if self.metodo_pago and self.metodo_pago.es_efectivo and self.con_cuanto_paga:
            return max(Decimal(str(self.con_cuanto_paga)) - Decimal(str(self.total)), Decimal('0'))
        return Decimal('0.00')
    
    def cancelar(self):
        """
        Cancela la venta y revierte el stock
        """
        if self.estado == 'activa':
            # Primero restauramos el stock
            detalles = self.detalles.all()
            for detalle in detalles:
                try:
                    # Restaurar stock al lote
                    lote = detalle.lote
                    lote.cantidad += detalle.cantidad
                    lote.save(update_fields=['cantidad'])
                except Exception as e:
                    # Manejo de errores
                    print(f"Error al restaurar stock: {e}")
                    continue
            
            # Revertir montos en el turno
            if self.turno.esta_activo():
                if self.metodo_pago and self.metodo_pago.es_efectivo:
                    # Restar del efectivo y sumar cambios dados
                    self.turno.monto_total_efectivo -= self.total
                    self.turno.total_cambios_dados -= self.cambio
                    self.turno.save(update_fields=['monto_total_efectivo', 'total_cambios_dados'])
                elif self.metodo_pago:
                    # Restar del medio de pago correspondiente
                    metodo = self.metodo_pago.nombre.lower()
                    if 'tarjeta' in metodo:
                        self.turno.monto_total_tarjeta -= self.total
                    elif 'transferencia' in metodo:
                        self.turno.monto_total_transferencia -= self.total
                    elif 'cheque' in metodo:
                        self.turno.monto_total_cheque -= self.total
                    self.turno.save()
            
            # Actualizar estado
            self.estado = 'cancelada'
            self.save(update_fields=['estado'])
            return True
        return False
    
    def actualizar_totales(self):
        """
        Actualiza el total de la venta basado en los detalles
        """
        detalles = self.detalles.all()
        self.total = sum(detalle.subtotal for detalle in detalles)
        self.save(update_fields=['total'])
    
    def registrar_en_turno(self):
        """
        Registra la venta en el turno relacionado
        """
        if not self.turno.esta_activo():
            return False
        
        if self.metodo_pago and self.metodo_pago.es_efectivo:
            # Actualizar efectivo y cambios
            self.turno.monto_total_efectivo += self.total
            self.turno.total_cambios_dados += self.cambio
            self.turno.save(update_fields=['monto_total_efectivo', 'total_cambios_dados'])
        elif self.metodo_pago:
            # Actualizar otros medios de pago
            metodo = self.metodo_pago.nombre.lower()
            if 'tarjeta' in metodo:
                self.turno.monto_total_tarjeta += self.total
                self.turno.save(update_fields=['monto_total_tarjeta'])
            elif 'transferencia' in metodo:
                self.turno.monto_total_transferencia += self.total
                self.turno.save(update_fields=['monto_total_transferencia'])
            elif 'cheque' in metodo:
                self.turno.monto_total_cheque += self.total
                self.turno.save(update_fields=['monto_total_cheque'])
        
        return True
    
    @classmethod
    def buscar_ventas(cls, usuario, fecha_inicio=None, fecha_fin=None, metodo_pago=None):
        """
        Búsqueda avanzada de ventas por diversos criterios
        """
        ventas = cls.objects.filter(usuario=usuario)
        
        if fecha_inicio:
            ventas = ventas.filter(fecha_hora__gte=fecha_inicio)
        
        if fecha_fin:
            ventas = ventas.filter(fecha_hora__lte=fecha_fin)
        
        if metodo_pago:
            ventas = ventas.filter(metodo_pago=metodo_pago)
        
        return ventas.order_by('-fecha_hora')
    
    def validar_pago_efectivo(self):
        """
        Valida si un pago en efectivo tiene monto suficiente
        """
        if self.metodo_pago and self.metodo_pago.es_efectivo:
            if not self.con_cuanto_paga:
                return False, "Debe ingresar el monto con el que paga el cliente"
            
            if self.con_cuanto_paga < self.total:
                return False, "El monto entregado es menor al total de la venta"
        
        return True, ""


# -------------------- DETALLE DE VENTA --------------------

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    lote = models.ForeignKey(InventarioProducto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_aplicado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
    
    class Meta:
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"
    
    def __str__(self):
        return f"{self.producto.nombre} - {self.cantidad} unidad(es)"
    
    def save(self, *args, **kwargs):
        """
        Sobreescribe el método save para calcular el subtotal automáticamente
        """
        # Calcular subtotal antes de guardar
        self.subtotal = self.calcular_subtotal()
        super().save(*args, **kwargs)
    
    def calcular_subtotal(self):
        """
        Calcula el subtotal considerando precio unitario, descuento y cantidad
        """
        return (Decimal(str(self.precio_unitario)) - Decimal(str(self.descuento_aplicado))) * self.cantidad


# -------------------- SIGNALS --------------------

@receiver(post_save, sender=DetalleVenta)
def actualizar_total_venta(sender, instance, created, **kwargs):
    """
    Actualiza el total de la venta cuando se crea o modifica un detalle
    """
    instance.venta.actualizar_totales()

@receiver(post_save, sender=Venta)
def registrar_venta_en_turno(sender, instance, created, **kwargs):
    """
    Registra la venta en el turno cuando se crea
    """
    if created and instance.estado == 'activa':
        instance.registrar_en_turno()

@receiver(pre_delete, sender=DetalleVenta)
def restaurar_stock_al_eliminar(sender, instance, **kwargs):
    """
    Restaura el stock al eliminar un detalle de venta
    """
    if instance.venta.estado == 'activa':
        try:
            lote = instance.lote
            lote.cantidad += instance.cantidad
            lote.save(update_fields=['cantidad'])
        except Exception as e:
            print(f"Error al restaurar stock: {e}")