from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
import os


# -------------------- Ruta personalizada para guardar cortes PDF --------------------

def ruta_pdf_corte(instance, filename):
    nombre_archivo = f"turno_{instance.id}_{instance.usuario.username}.pdf"
    return os.path.join('cortes_cajas', nombre_archivo)


# -------------------- MODELO DE TURNO --------------------

class Turno(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('finalizado', 'Finalizado'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='turnos')
    hora_inicio = models.DateTimeField(default=timezone.now)
    hora_fin_estimada = models.DateTimeField(verbose_name="Hora de fin estimada")
    hora_fin_real = models.DateTimeField(blank=True, null=True)

    monto_inicial = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Monto en efectivo con el que inició el turno"
    )

    monto_total_efectivo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monto_total_tarjeta = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monto_total_transferencia = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monto_total_cheque = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    total_cambios_dados = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Suma total de los cambios entregados en ventas en efectivo"
    )

    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activo')
    pdf_reporte = models.FileField(upload_to=ruta_pdf_corte, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Turno #{self.id} - {self.usuario.username} ({self.estado})"

    def total_ventas_turno(self):
        return (
            self.monto_total_efectivo +
            self.monto_total_tarjeta +
            self.monto_total_transferencia +
            self.monto_total_cheque
        )

    def efectivo_en_caja(self):
        """
        Retorna el efectivo acumulado: monto inicial + ventas en efectivo
        """
        return self.monto_inicial + self.monto_total_efectivo

    def efectivo_final_en_caja(self):
        """
        Retorna el efectivo final: efectivo acumulado - cambios dados
        """
        return self.efectivo_en_caja() - self.total_cambios_dados

    def esta_activo(self):
        return self.estado == 'activo'

    def finalizar(self, hora_fin_real, reporte_pdf=None):
        """
        Método para finalizar turno y generar resumen (se puede usar en views).
        """
        self.hora_fin_real = hora_fin_real
        self.estado = 'finalizado'
        if reporte_pdf:
            self.pdf_reporte = reporte_pdf
        self.save()
