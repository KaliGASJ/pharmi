from django import forms
from .models import Turno
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

# -------------------- FORMULARIO PARA INICIAR TURNO --------------------

class IniciarTurnoForm(forms.ModelForm):
    hora_fin_estimada = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        }),
        label="Hora de fin estimada",
        required=True,
        initial=timezone.localtime(timezone.now() + timedelta(hours=8))
    )
    
    monto_inicial = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=2,
        label="Monto inicial en caja ($)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Ingrese el monto inicial en caja'
        })
    )

    class Meta:
        model = Turno
        fields = ['hora_fin_estimada', 'monto_inicial']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Establecer valores iniciales si no se han proporcionado
        if not self.initial.get('hora_fin_estimada'):
            # Establecer hora de fin estimada por defecto (8 horas después)
            self.initial['hora_fin_estimada'] = timezone.localtime(timezone.now() + timedelta(hours=8))

    def clean_hora_fin_estimada(self):
        hora_fin = self.cleaned_data['hora_fin_estimada']
        hora_actual = timezone.now()
        
        if hora_fin <= hora_actual:
            raise forms.ValidationError("La hora de fin debe ser posterior a la hora actual.")
        
        # Verificar que no sea más de 24 horas después
        if hora_fin > hora_actual + timedelta(hours=24):
            raise forms.ValidationError("La hora de fin no puede ser más de 24 horas después de la hora actual.")
            
        return hora_fin

    def clean_monto_inicial(self):
        monto = self.cleaned_data.get('monto_inicial')
        if monto is None:
            raise forms.ValidationError("Debe ingresar un monto inicial.")
        
        if monto < 0:
            raise forms.ValidationError("El monto inicial no puede ser negativo.")
            
        # Convertir a Decimal para evitar errores de precisión
        return Decimal(str(monto))


# -------------------- FORMULARIO PARA FINALIZAR TURNO --------------------

class FinalizarTurnoForm(forms.ModelForm):
    hora_fin_real = forms.DateTimeField(
        widget=forms.HiddenInput(),
        initial=timezone.now
    )
    
    # Campo para observaciones o notas adicionales al finalizar turno
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observaciones opcionales sobre el cierre de turno'
        }),
        label="Observaciones (opcional)"
    )

    class Meta:
        model = Turno
        fields = ['hora_fin_real', 'observaciones']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Establecer la hora actual como hora de fin por defecto
        if not self.initial.get('hora_fin_real'):
            self.initial['hora_fin_real'] = timezone.now()

    def save(self, commit=True):
        turno = super().save(commit=False)
        turno.estado = 'finalizado'
        
        # Asegurar que la hora de fin no sea anterior a la hora de inicio
        if turno.hora_fin_real < turno.hora_inicio:
            turno.hora_fin_real = timezone.now()
            
        if commit:
            turno.save()
        return turno


# -------------------- FORMULARIO PARA FILTRAR TURNOS POR FECHA --------------------

class FiltroTurnoForm(forms.Form):
    fecha = forms.DateField(
        label="Fecha",
        required=True,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'max': date.today().isoformat()
        }),
        initial=date.today
    )
    
    def clean_fecha(self):
        fecha_seleccionada = self.cleaned_data.get('fecha')
        if fecha_seleccionada > date.today():
            raise forms.ValidationError("No puede seleccionar una fecha futura.")
        return fecha_seleccionada