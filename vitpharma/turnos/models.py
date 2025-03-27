from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from weasyprint import HTML
from decimal import Decimal
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
    observaciones = models.TextField(blank=True, null=True, help_text="Notas internas del turno")
    cerrado_automaticamente = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = "Turno"
        verbose_name_plural = "Turnos"

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
        return self.monto_inicial + self.monto_total_efectivo

    def efectivo_final_en_caja(self):
        return self.efectivo_en_caja() - self.total_cambios_dados

    def esta_activo(self):
        return self.estado == 'activo'

    def ha_expirado(self):
        return self.estado == 'activo' and timezone.now() > self.hora_fin_estimada

    def verificar_finalizacion_automatica(self):
        if self.ha_expirado():
            self.finalizar(hora_fin_real=timezone.now(), cerrado_automaticamente=True)
            return True
        return False

    def actualizar_monto_efectivo(self, monto, es_ingreso=True):
        monto = Decimal(str(monto))
        if es_ingreso:
            self.monto_total_efectivo += monto
        else:
            self.monto_total_efectivo -= monto
        self.save(update_fields=['monto_total_efectivo'])
        return True

    def actualizar_cambios_dados(self, cambio):
        self.total_cambios_dados += Decimal(str(cambio))
        self.save(update_fields=['total_cambios_dados'])
        return True

    def actualizar_montos_otros_medios(self, monto, tipo_pago):
        monto = Decimal(str(monto))
        tipo_pago = tipo_pago.lower()
        if 'tarjeta' in tipo_pago:
            self.monto_total_tarjeta += monto
            self.save(update_fields=['monto_total_tarjeta'])
        elif 'transferencia' in tipo_pago:
            self.monto_total_transferencia += monto
            self.save(update_fields=['monto_total_transferencia'])
        elif 'cheque' in tipo_pago:
            self.monto_total_cheque += monto
            self.save(update_fields=['monto_total_cheque'])
        else:
            return False
        return True

    def registrar_venta(self, monto, tipo_pago, cambio=0):
        tipo_pago = tipo_pago.lower()
        if 'efectivo' in tipo_pago:
            self.actualizar_monto_efectivo(monto)
            if cambio > 0:
                self.actualizar_cambios_dados(cambio)
        else:
            self.actualizar_montos_otros_medios(monto, tipo_pago)
        return True

    def revertir_venta(self, monto, tipo_pago, cambio=0):
        tipo_pago = tipo_pago.lower()
        if 'efectivo' in tipo_pago:
            self.actualizar_monto_efectivo(monto, es_ingreso=False)
            if cambio > 0:
                self.total_cambios_dados -= Decimal(str(cambio))
                self.save(update_fields=['total_cambios_dados'])
        else:
            monto = Decimal(str(monto))
            if 'tarjeta' in tipo_pago:
                self.monto_total_tarjeta -= monto
                self.save(update_fields=['monto_total_tarjeta'])
            elif 'transferencia' in tipo_pago:
                self.monto_total_transferencia -= monto
                self.save(update_fields=['monto_total_transferencia'])
            elif 'cheque' in tipo_pago:
                self.monto_total_cheque -= monto
                self.save(update_fields=['monto_total_cheque'])
        return True

    @classmethod
    def obtener_turnos_por_fecha(cls, usuario, fecha):
        fecha_inicio = timezone.datetime.combine(fecha, timezone.datetime.min.time())
        fecha_fin = timezone.datetime.combine(fecha, timezone.datetime.max.time())
        return cls.objects.filter(
            usuario=usuario,
            hora_inicio__gte=fecha_inicio,
            hora_inicio__lte=fecha_fin
        ).order_by('-hora_inicio')

    @classmethod
    def obtener_turno_activo(cls, usuario):
        return cls.objects.filter(usuario=usuario, estado='activo').first()

    def finalizar(self, hora_fin_real=None, cerrado_automaticamente=False):
        if not hora_fin_real:
            hora_fin_real = timezone.now()

        self.hora_fin_real = hora_fin_real
        self.estado = 'finalizado'
        self.cerrado_automaticamente = cerrado_automaticamente

        # --------- Generación automática del PDF ---------
        html_string = render_to_string('corte_turno.html', {'turno': self})
        pdf_file = HTML(string=html_string).write_pdf()
        nombre_archivo = f"corte_turno_{self.id}_{self.usuario.username}.pdf"
        self.pdf_reporte.save(nombre_archivo, ContentFile(pdf_file), save=False)

        self.save(update_fields=['hora_fin_real', 'estado', 'cerrado_automaticamente', 'pdf_reporte'])
        return True

    @property
    def duracion_turno(self):
        if self.hora_fin_real:
            return self.hora_fin_real - self.hora_inicio
        return timezone.now() - self.hora_inicio
