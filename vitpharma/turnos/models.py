from django.db import models
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from weasyprint import HTML
from io import BytesIO
from django.core.files.base import ContentFile
from decimal import Decimal
from datetime import datetime

class Turno(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='turnos')

    fecha = models.DateField(auto_now_add=True)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    monto_inicial = models.DecimalField("Efectivo inicial", max_digits=10, decimal_places=2, default=Decimal('0.00'))
    monto_final = models.DecimalField("Efectivo final", max_digits=10, decimal_places=2, null=True, blank=True)

    esta_activo = models.BooleanField(default=True)
    archivo_corte = models.FileField(upload_to='cortes_caja/', null=True, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Turno"
        verbose_name_plural = "Turnos"
        ordering = ['-fecha', '-hora_inicio']

    def __str__(self):
        return f"Turno #{self.id} - {self.usuario.username} ({self.fecha})"

    def obtener_ventas(self):
        """Retorna todas las ventas asociadas al turno actual."""
        return self.ventas.all()

    def total_ventas(self):
        """Calcula el monto total de ventas durante el turno."""
        return self.ventas.aggregate(models.Sum('total'))['total__sum'] or Decimal('0.00')

    def cantidad_ventas(self):
        """Retorna la cantidad de ventas realizadas durante el turno."""
        return self.ventas.count()
    
    def hay_ventas(self):
        """Verifica si hay ventas asociadas al turno."""
        return self.ventas.exists()

    def generar_corte_caja_pdf(self):
        """
        Genera y guarda un PDF con el corte de caja del turno.
        Debe llamarse cuando el turno es finalizado.
        """
        from ventas.models import Venta

        ventas_turno = self.ventas.all()
        total_general = ventas_turno.aggregate(models.Sum('total'))['total__sum'] or Decimal('0.00')

        ventas_por_metodo = ventas_turno.values('metodo_pago__nombre') \
            .annotate(total=models.Sum('total'), cantidad=models.Count('id')) \
            .order_by('metodo_pago__nombre')

        # Análisis adicionales para el corte
        # Productos más vendidos
        productos_vendidos = {}
        for venta in ventas_turno:
            for detalle in venta.detalles.all():
                producto = detalle.lote_vendido.producto.nombre
                if producto in productos_vendidos:
                    productos_vendidos[producto] += detalle.cantidad
                else:
                    productos_vendidos[producto] = detalle.cantidad
        
        productos_top = sorted(
            [{"nombre": k, "cantidad": v} for k, v in productos_vendidos.items()],
            key=lambda x: x["cantidad"],
            reverse=True
        )[:5]  # Top 5 productos

        context = {
            'turno': self,
            'ventas': ventas_turno,
            'total_general': total_general,
            'ventas_por_metodo': ventas_por_metodo,
            'productos_top': productos_top,
            'total_productos_vendidos': sum(productos_vendidos.values()) if productos_vendidos else 0
        }

        html_string = render_to_string('corte_caja_template.html', context)
        html = HTML(string=html_string)

        pdf_file = BytesIO()
        html.write_pdf(target=pdf_file)
        pdf_file.seek(0)

        # 👇 Nombre único para evitar caché del navegador
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"corte_turno_{self.id}_{timestamp}.pdf"

        # Guardar el archivo en el campo archivo_corte
        self.archivo_corte.save(file_name, ContentFile(pdf_file.read()), save=False)
        self.save()