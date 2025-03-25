from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
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
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = "Turno"
        verbose_name_plural = "Turnos"

    def __str__(self):
        return f"Turno #{self.id} - {self.usuario.username} ({self.estado})"

    def total_ventas_turno(self):
        """
        Calcula el total de ventas del turno sumando todos los medios de pago
        """
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
        """
        Verifica si el turno está activo
        """
        return self.estado == 'activo'

    def ha_expirado(self):
        """
        Verifica si el turno ha expirado basado en la hora de fin estimada
        """
        return self.estado == 'activo' and timezone.now() > self.hora_fin_estimada

    def verificar_finalizacion_automatica(self):
        """
        Finaliza automáticamente el turno si ha expirado
        """
        if self.ha_expirado():
            self.finalizar(timezone.now())
            return True
        return False

    def actualizar_monto_efectivo(self, monto, es_ingreso=True):
        """
        Actualiza el monto de efectivo en el turno
        """
        monto = Decimal(str(monto))
        if es_ingreso:
            self.monto_total_efectivo += monto
        else:
            self.monto_total_efectivo -= monto
        self.save(update_fields=['monto_total_efectivo'])
        return True

    def actualizar_cambios_dados(self, cambio):
        """
        Actualiza el total de cambios dados en ventas
        """
        self.total_cambios_dados += Decimal(str(cambio))
        self.save(update_fields=['total_cambios_dados'])
        return True

    def actualizar_montos_otros_medios(self, monto, tipo_pago):
        """
        Actualiza los montos de otros medios de pago (tarjeta, transferencia, cheque)
        """
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
        """
        Registra una venta en el turno según el tipo de pago
        """
        tipo_pago = tipo_pago.lower()
        
        if 'efectivo' in tipo_pago:
            self.actualizar_monto_efectivo(monto)
            if cambio > 0:
                self.actualizar_cambios_dados(cambio)
        else:
            self.actualizar_montos_otros_medios(monto, tipo_pago)
        
        return True

    def revertir_venta(self, monto, tipo_pago, cambio=0):
        """
        Revierte una venta registrada previamente
        """
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
        """
        Obtiene los turnos según la fecha especificada
        """
        fecha_inicio = timezone.datetime.combine(fecha, timezone.datetime.min.time())
        fecha_fin = timezone.datetime.combine(fecha, timezone.datetime.max.time())
        
        return cls.objects.filter(
            usuario=usuario,
            hora_inicio__gte=fecha_inicio,
            hora_inicio__lte=fecha_fin
        ).order_by('-hora_inicio')

    @classmethod
    def obtener_turno_activo(cls, usuario):
        """
        Obtiene el turno activo del usuario, si existe
        """
        return cls.objects.filter(usuario=usuario, estado='activo').first()

    def finalizar(self, hora_fin_real=None, reporte_pdf=None):
        """
        Método para finalizar turno y generar resumen
        """
        if not hora_fin_real:
            hora_fin_real = timezone.now()
            
        self.hora_fin_real = hora_fin_real
        self.estado = 'finalizado'
        
        if reporte_pdf:
            self.pdf_reporte = reporte_pdf
            
        self.save(update_fields=['hora_fin_real', 'estado', 'pdf_reporte'])
        return True