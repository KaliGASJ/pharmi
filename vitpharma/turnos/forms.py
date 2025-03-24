from django import forms
from .models import Turno
from datetime import time

class IniciarTurnoForm(forms.ModelForm):
    hora_inicio = forms.TimeField(
        widget=forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control'}),
        label="Hora de inicio",
        help_text="Formato: HH:MM (24 horas)",
        required=True
    )
    
    hora_fin = forms.TimeField(
        widget=forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control'}),
        label="Hora de fin estimada",
        help_text="Formato: HH:MM (24 horas)",
        required=True,
        initial=None  # Eliminar cualquier valor inicial
    )
    
    monto_inicial = forms.DecimalField(
        label="Monto inicial en caja ($)",
        min_value=0,
        max_digits=10,
        decimal_places=2,
        initial=0.00,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    class Meta:
        model = Turno
        fields = ['hora_inicio', 'hora_fin', 'monto_inicial']
       
    def clean_hora_inicio(self):
        """Validar que la hora de inicio esté en el rango válido."""
        hora_inicio = self.cleaned_data.get('hora_inicio')
        if hora_inicio and (hora_inicio.hour < 0 or hora_inicio.hour > 23):
            raise forms.ValidationError("La hora debe estar entre 0 y 23")
        return hora_inicio
       
    def clean_hora_fin(self):
        """Validar que la hora de fin esté en el rango válido."""
        hora_fin = self.cleaned_data.get('hora_fin')
        if hora_fin and (hora_fin.hour < 0 or hora_fin.hour > 23):
            raise forms.ValidationError("La hora debe estar entre 0 y 23")
        return hora_fin
   
    def clean(self):
        """Validación adicional para comparar hora_inicio y hora_fin."""
        cleaned_data = super().clean()
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_fin = cleaned_data.get('hora_fin')
       
        if hora_inicio and hora_fin:
            # Convertir horas a minutos para comparación fácil
            minutos_inicio = hora_inicio.hour * 60 + hora_inicio.minute
            minutos_fin = hora_fin.hour * 60 + hora_fin.minute
           
            # Si la hora de fin es anterior a la de inicio, asumimos que es el día siguiente
            if minutos_fin < minutos_inicio:
                # Está bien, es turno nocturno
                pass
            elif minutos_fin == minutos_inicio:
                self.add_error('hora_fin', "La hora de fin debe ser diferente a la hora de inicio")
            elif minutos_fin - minutos_inicio < 60:
                self.add_error('hora_fin', "El turno debe durar al menos 1 hora")
               
        return cleaned_data