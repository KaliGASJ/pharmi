from django import forms
from .models import Turno
from django.utils import timezone


# -------------------- FORMULARIO PARA INICIAR TURNO --------------------

class IniciarTurnoForm(forms.ModelForm):
    hora_fin_estimada = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label="Hora de fin estimada"
    )
    monto_inicial = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=2,
        label="Monto inicial en caja ($)"
    )

    class Meta:
        model = Turno
        fields = ['hora_fin_estimada', 'monto_inicial']

    def clean_hora_fin_estimada(self):
        hora_fin = self.cleaned_data['hora_fin_estimada']
        if hora_fin <= timezone.now():
            raise forms.ValidationError("La hora de fin debe ser posterior a la hora actual.")
        return hora_fin


# -------------------- FORMULARIO PARA FINALIZAR TURNO --------------------

class FinalizarTurnoForm(forms.ModelForm):
    hora_fin_real = forms.DateTimeField(
        widget=forms.HiddenInput()
    )

    class Meta:
        model = Turno
        fields = ['hora_fin_real']

    def save(self, commit=True):
        turno = super().save(commit=False)
        turno.estado = 'finalizado'
        if commit:
            turno.save()
        return turno
