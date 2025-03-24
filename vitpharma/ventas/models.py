from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from turnos.models import Turno
from inventario.models import InventarioProducto, Producto  # Agregamos Producto para referencias
from django.template.loader import render_to_string
from weasyprint import HTML
from io import BytesIO
from django.core.files.base import ContentFile
from decimal import Decimal
from datetime import datetime

# -------------------- MÉTODO DE PAGO --------------------
class MetodoPago(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=40, unique=True)
    
    # Mantenemos consistencia con otros modelos del sistema
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
    fecha_modificacion = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        verbose_name = "Método de pago"
        verbose_name_plural = "Métodos de pago"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


# -------------------- VENTA --------------------
class Venta(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ventas')
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name='ventas')
    fecha_hora = models.DateTimeField(auto_now_add=True)

    total = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.SET_NULL, null=True, blank=True)

    generado_ticket = models.BooleanField(default=False)
    archivo_ticket = models.FileField(upload_to='tickets/', null=True, blank=True)

    # Campos de auditoría consistentes con otros modelos
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)
    usuario_registro = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="registro_venta"
    )
    usuario_modificacion = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="modificacion_venta"
    )

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"Venta #{self.id} - {self.usuario.username} - ${self.total}"

    def clean(self):
        super().clean()
        # Verificar que haya un turno activo asignado
        if not self.turno:
            turno_activo = Turno.objects.filter(
                usuario=self.usuario, 
                esta_activo=True
            ).first()
            
            if not turno_activo:
                raise ValidationError(
                    "No es posible registrar una venta sin un turno activo. "
                    "Por favor inicie un turno primero."
                )
            
            self.turno = turno_activo
        
        # Verificar que el turno esté activo
        elif not self.turno.esta_activo:
            raise ValidationError("No se puede asignar una venta a un turno finalizado.")

    def asignar_a_turno(self, turno=None):
        """
        Asigna la venta al turno activo del usuario o al turno especificado.
        Retorna True si fue exitoso, False en caso contrario.
        """
        if turno is None:
            # Buscar el turno activo del usuario
            turno = Turno.objects.filter(
                usuario=self.usuario, 
                esta_activo=True
            ).first()
            
        if turno and turno.esta_activo:
            self.turno = turno
            self.save()
            return True
        return False

    def calcular_total(self):
        """Calcula el total de la venta a partir de los detalles"""
        total = sum(detalle.subtotal for detalle in self.detalles.all())
        self.total = total
        return total

    def actualizar_inventario(self):
        """Actualiza el inventario después de una venta"""
        for detalle in self.detalles.all():
            lote = detalle.lote_vendido
            if lote.cantidad >= detalle.cantidad:
                lote.cantidad -= detalle.cantidad
                lote.save()
            else:
                raise ValidationError(f"Stock insuficiente para {lote.producto.nombre} (Lote: {lote.lote})")

    def generar_ticket_pdf(self):
        """
        Genera y guarda el PDF del ticket en base a la plantilla HTML.
        """
        context = {
            'venta': self,
            'detalles': self.detalles.all(),
            'fecha_hora': self.fecha_hora,
            'turno': self.turno,
            'usuario': self.usuario
        }
        
        html_string = render_to_string('ticket_template.html', context)
        html = HTML(string=html_string)

        pdf_file = BytesIO()
        html.write_pdf(target=pdf_file)
        pdf_file.seek(0)

        # 👇 Nombre único para evitar caché del navegador
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"ticket_venta_{self.id}_{timestamp}.pdf"
        
        self.archivo_ticket.save(file_name, ContentFile(pdf_file.read()), save=True)
        self.generado_ticket = True
        self.save(update_fields=['generado_ticket', 'modificado_en'])

    def save(self, *args, **kwargs):
        # Si es una nueva venta (sin ID), verificar turno activo
        if not self.id:
            # Verificar que haya un turno asignado
            if not self.turno:
                turno_activo = Turno.objects.filter(
                    usuario=self.usuario, 
                    esta_activo=True
                ).first()
                
                if turno_activo:
                    self.turno = turno_activo
                    
                    # Si no hay usuario_registro, asignar el usuario actual
                    if not self.usuario_registro:
                        self.usuario_registro = self.usuario

        super().save(*args, **kwargs)


# -------------------- DETALLE DE VENTA --------------------
class DetalleVenta(models.Model):
    id = models.AutoField(primary_key=True)
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')

    lote_vendido = models.ForeignKey(
        InventarioProducto,
        on_delete=models.PROTECT,
        related_name='detalles_venta',
        help_text="Lote específico del producto vendido"
    )

    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    total_descuento = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0.00,
        help_text="Total descontado = cantidad * descuento_unitario"
    )

    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Total = (precio_unitario * cantidad) - total_descuento"
    )

    # Campos de auditoría
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"

    def __str__(self):
        return f"{self.lote_vendido.producto.nombre} x {self.cantidad} (Venta #{self.venta.id})"

    def clean(self):
        super().clean()
        # Verificar stock disponible
        if self.lote_vendido and self.cantidad > self.lote_vendido.cantidad:
            raise ValidationError(
                f"Stock insuficiente para {self.lote_vendido.producto.nombre}. "
                f"Disponible: {self.lote_vendido.cantidad}, Solicitado: {self.cantidad}"
            )

    def calcular_subtotal(self):
        """
        Calcula subtotal y total_descuento aplicados al detalle.
        """
        self.total_descuento = self.cantidad * self.descuento_unitario
        self.subtotal = (self.cantidad * self.precio_unitario) - self.total_descuento
        return self.subtotal

    def save(self, *args, **kwargs):
        # Calcular subtotal antes de guardar si no se ha calculado
        if not self.subtotal or self.subtotal == 0:
            self.calcular_subtotal()
        super().save(*args, **kwargs)