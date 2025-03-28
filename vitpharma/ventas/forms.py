from django import forms
from decimal import Decimal
from .models import Venta


# -------------------- FORMULARIO PARA REGISTRAR UNA VENTA --------------------

class VentaForm(forms.ModelForm):
    """
    Formulario principal para registrar una venta.
    Solo muestra 'con cuánto paga' si el método de pago es efectivo.
    """
    class Meta:
        model = Venta
        fields = ['metodo_pago', 'con_cuanto_paga']
        widgets = {
            'metodo_pago': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'con_cuanto_paga': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Ingrese con cuánto paga el cliente (solo efectivo)'
            }),
        }
        labels = {
            'metodo_pago': 'Método de pago',
            'con_cuanto_paga': 'Con cuánto paga (solo efectivo)',
        }

    def clean(self):
        cleaned_data = super().clean()
        metodo = cleaned_data.get('metodo_pago')
        con_cuanto_paga = cleaned_data.get('con_cuanto_paga')

        if metodo and metodo.es_efectivo:
            if con_cuanto_paga is None:
                self.add_error('con_cuanto_paga', "Debe ingresar con cuánto paga el cliente.")
            elif con_cuanto_paga <= Decimal('0.00'):
                self.add_error('con_cuanto_paga', "El monto debe ser mayor a cero.")
        else:
            # Si el método NO es efectivo, limpiamos el campo
            cleaned_data['con_cuanto_paga'] = None

        return cleaned_data


# -------------------- FORMULARIO DE CONFIRMACIÓN PARA CANCELAR VENTA --------------------

class CancelarVentaForm(forms.Form):
    """
    Formulario de confirmación para cancelar una venta.
    Se utiliza para evitar cancelaciones accidentales.
    """
    confirmacion = forms.BooleanField(
        required=True,
        label="Confirmo que deseo cancelar esta venta",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
