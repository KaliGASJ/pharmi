from django import forms
from .models import Venta, DetalleVenta
from inventario.models import Producto, InventarioProducto
from django.forms import inlineformset_factory


# -------------------- FORMULARIO DE REGISTRO DE VENTA --------------------

class VentaForm(forms.ModelForm):
    con_cuanto_paga = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=0,
        label="¿Con cuánto paga?",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Solo efectivo'})
    )

    class Meta:
        model = Venta
        fields = ['metodo_pago', 'con_cuanto_paga']
        widgets = {
            'metodo_pago': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'Selecciona el método de pago'
            }),
        }
        labels = {
            'metodo_pago': 'Método de Pago'
        }

    def clean(self):
        cleaned_data = super().clean()
        metodo_pago = cleaned_data.get('metodo_pago')
        con_cuanto_paga = cleaned_data.get('con_cuanto_paga')
        total = self.instance.total if self.instance and self.instance.total else 0

        if metodo_pago and "efectivo" in metodo_pago.nombre.lower():
            if con_cuanto_paga is None:
                raise forms.ValidationError("Debes ingresar con cuánto paga el cliente.")
            if total and con_cuanto_paga < total:
                raise forms.ValidationError("El monto entregado es menor al total de la venta.")
        return cleaned_data


# -------------------- FORMULARIO PARA AGREGAR DETALLES A LA VENTA --------------------

class DetalleVentaForm(forms.ModelForm):
    class Meta:
        model = DetalleVenta
        fields = ['producto', 'lote', 'cantidad', 'precio_unitario', 'descuento_aplicado']

        widgets = {
            'producto': forms.Select(attrs={'class': 'form-control'}),
            'lote': forms.Select(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Cantidad'
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Precio unitario'
            }),
            'descuento_aplicado': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Descuento'
            }),
        }
        labels = {
            'producto': 'Producto',
            'lote': 'Lote',
            'cantidad': 'Cantidad',
            'precio_unitario': 'Precio Unitario',
            'descuento_aplicado': 'Descuento'
        }

    def clean(self):
        cleaned_data = super().clean()
        cantidad = cleaned_data.get('cantidad')
        lote = cleaned_data.get('lote')

        if lote and cantidad:
            if cantidad > lote.cantidad:
                raise forms.ValidationError(f"No hay suficiente stock en el lote seleccionado ({lote.codigo_lote}).")
        return cleaned_data


# -------------------- FORMSET PARA DETALLES DE VENTA --------------------

DetalleVentaFormSet = inlineformset_factory(
    Venta,
    DetalleVenta,
    form=DetalleVentaForm,
    extra=1,
    can_delete=True
)
