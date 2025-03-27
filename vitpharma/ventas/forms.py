from django import forms
from .models import Venta
from decimal import Decimal


# -------------------- FORMULARIO PARA REGISTRAR UNA VENTA --------------------

class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['metodo_pago', 'con_cuanto_paga']
        widgets = {
            'metodo_pago': forms.Select(attrs={'class': 'form-select'}),
            'con_cuanto_paga': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Ingrese con cuánto paga el cliente'
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
            # Si el método NO es efectivo, ignoramos el campo
            cleaned_data['con_cuanto_paga'] = None

        return cleaned_data


# -------------------- FORMULARIO DE CONFIRMACIÓN PARA CANCELAR VENTA --------------------

class CancelarVentaForm(forms.Form):
    confirmacion = forms.BooleanField(
        label="Confirmo que deseo cancelar esta venta",
        required=True
    )
