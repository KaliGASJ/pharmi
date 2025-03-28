from django import forms
from django.utils import timezone
from .models import Turno


class AperturaTurnoForm(forms.ModelForm):
    """
    Formulario para iniciar un nuevo turno.
    Permite ingresar la hora estimada de cierre y el monto inicial en caja.
    """
    class Meta:
        model = Turno
        fields = ['hora_fin_estimada', 'monto_inicial']
        widgets = {
            'hora_fin_estimada': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'required': True,
            }),
            'monto_inicial': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'placeholder': '0.00',
                'required': True,
            }),
        }
        labels = {
            'hora_fin_estimada': 'Hora estimada de cierre',
            'monto_inicial': 'Monto inicial en caja (efectivo)',
        }

    def clean_hora_fin_estimada(self):
        """
        Valida que la hora estimada de cierre no sea en el pasado.
        """
        hora_fin = self.cleaned_data.get('hora_fin_estimada')
        if hora_fin <= timezone.now():
            raise forms.ValidationError("La hora estimada de cierre debe ser posterior al momento actual.")
        return hora_fin


class FinalizarTurnoForm(forms.ModelForm):
    """
    Formulario para finalizar manualmente un turno.
    Permite registrar la hora de cierre real y observaciones.
    """
    class Meta:
        model = Turno
        fields = ['hora_fin_real', 'observaciones']
        widgets = {
            'hora_fin_real': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'required': True,
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notas adicionales del turno (opcional)',
            }),
        }
        labels = {
            'hora_fin_real': 'Hora real de cierre',
            'observaciones': 'Observaciones finales',
        }
