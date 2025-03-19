from django.db import models
class Reporte(models.Model):
    id_reporte = models.AutoField(primary_key=True)
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    tipo_reporte = models.CharField(max_length=50)  # Inventario, Ventas, etc.
    archivo = models.FileField(upload_to="reportes/")

    def __str__(self):
        return f"Reporte {self.tipo_reporte} - {self.fecha_generacion.strftime('%Y-%m-%d')}"

# Create your models here.