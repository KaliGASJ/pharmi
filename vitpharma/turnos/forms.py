from django import forms
from .models import Turno
from datetime import time

class IniciarTurnoForm(forms.ModelForm):
    hora_inicio = forms.TimeField(
        widget=forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
        label="Hora de inicio",
    )

    hora_fin = forms.TimeField(
        widget=forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
        label="Hora de fin estimada",
    )

    monto_inicial = forms.DecimalField(
        label="Monto inicial en caja ($)",
        min_value=0,
        max_digits=10,
        decimal_places=2,
        initial=0.00
    )

    class Meta:
        model = Turno
        fields = ['hora_inicio', 'hora_fin', 'monto_inicial']
