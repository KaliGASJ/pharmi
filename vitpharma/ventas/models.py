from django.db import models
from django.contrib.auth.models import User
from turnos.models import Turno
from inventario.models import InventarioProducto  # Nos relacionamos con el lote, no solo con el producto
from django.template.loader import render_to_string
from weasyprint import HTML
from io import BytesIO
from django.core.files.base import ContentFile

# -------------------- MÉTODO DE PAGO --------------------

class MetodoPago(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=40, unique=True)

    class Meta:
        verbose_name = "Método de pago"
        verbose_name_plural = "Métodos de pago"

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

    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"Venta #{self.id} - {self.usuario.username} - ${self.total}"

    def generar_ticket_pdf(self):
        """
        Genera y guarda el PDF del ticket en base a la plantilla HTML.
        """
        html_string = render_to_string('ticket_template.html', {'venta': self})
        html = HTML(string=html_string)

        pdf_file = BytesIO()
        html.write_pdf(target=pdf_file)
        pdf_file.seek(0)

        file_name = f"ticket_venta_{self.id}.pdf"
        self.archivo_ticket.save(file_name, ContentFile(pdf_file.read()), save=True)
        self.generado_ticket = True
        self.save()

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

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"

    def __str__(self):
        return f"{self.lote_vendido.producto.nombre} x {self.cantidad} (Venta #{self.venta.id})"

    def calcular_subtotal(self):
        """
        Calcula subtotal y total_descuento aplicados al detalle.
        """
        self.total_descuento = self.cantidad * self.descuento_unitario
        self.subtotal = (self.cantidad * self.precio_unitario) - self.total_descuento
        return self.subtotal
