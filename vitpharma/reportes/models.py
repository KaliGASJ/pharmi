from django.db import models
from django.contrib.auth.models import User

class LogReporteGenerado(models.Model):
    """
    Registro de cada reporte generado por un administrador.
    Esto permite llevar trazabilidad y control de auditoría.
    """
    TIPO_REPORTE_CHOICES = [
        ('cajas_general', 'Reporte de Cajas General'),
        ('cortes_historial', 'Historial de Cortes de Cajas'),
        ('ventas_historial', 'Historial de Ventas'),
        ('inventario', 'Reporte de Inventario'),
        ('proveedores', 'Reporte de Proveedores'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_reporte = models.CharField(max_length=30, choices=TIPO_REPORTE_CHOICES)
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    parametros = models.TextField(blank=True, null=True, help_text="Parámetros utilizados en la generación del reporte (ej. rango de fechas).")

    class Meta:
        verbose_name = "Log de reporte"
        verbose_name_plural = "Logs de reportes"
        ordering = ['-fecha_generacion']

    def __str__(self):
        return f"{self.get_tipo_reporte_display()} - {self.usuario.username if self.usuario else 'N/A'} - {self.fecha_generacion.strftime('%Y-%m-%d %H:%M')}"
