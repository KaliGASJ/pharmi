from django import forms
from .models import Conversacion

class PreguntaForm(forms.ModelForm):
    class Meta:
        model = Conversacion
        fields = ['pregunta']
        widgets = {
            'pregunta': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Escribe tu pregunta aquí...',
                'style': 'resize: none;'
            }),
        }
        labels = {
            'pregunta': '',
        }
