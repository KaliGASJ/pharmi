from django import forms
from .models import Turno


class AperturaTurnoForm(forms.ModelForm):
    class Meta:
        model = Turno
        fields = ['hora_fin_estimada', 'monto_inicial']
        widgets = {
            'hora_fin_estimada': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'monto_inicial': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
        }
        labels = {
            'hora_fin_estimada': 'Hora de cierre estimada',
            'monto_inicial': 'Monto inicial en caja (efectivo)',
        }


class FinalizarTurnoForm(forms.ModelForm):
    class Meta:
        model = Turno
        fields = ['hora_fin_real', 'observaciones']
        widgets = {
            'hora_fin_real': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
        labels = {
            'hora_fin_real': 'Hora de cierre real',
            'observaciones': 'Observaciones finales (opcional)',
        }
