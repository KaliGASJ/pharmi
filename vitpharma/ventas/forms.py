from django import forms
from .models import Venta, DetalleVenta, MetodoPago
from inventario.models import Producto, InventarioProducto
from turnos.models import Turno
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.db.models import Q
from decimal import Decimal
import json


# -------------------- FORMULARIO DE BÚSQUEDA DE PRODUCTOS --------------------

class BusquedaProductoForm(forms.Form):
    """
    Formulario para buscar productos por nombre o código de barras
    """
    busqueda = forms.CharField(
        max_length=100,
        required=False,
        label='',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '🔍 Buscar por nombre o código de barras',
            'autocomplete': 'off',
            'id': 'buscar-producto'
        })
    )


# -------------------- FORMULARIO DE REGISTRO DE VENTA --------------------

class VentaForm(forms.ModelForm):
    con_cuanto_paga = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=0,
        label="¿Con cuánto paga?",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Solo efectivo',
            'step': '0.01',
            'id': 'con-cuanto-paga'
        })
    )
    
    # Campo oculto para almacenar los detalles del carrito
    carrito_json = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'carrito-json'})
    )
    
    # Campo para mostrar el total de la venta (solo visualización)
    total_venta = forms.DecimalField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'id': 'total-venta'
        }),
        label="Total a pagar"
    )
    
    # Campo para mostrar el cambio calculado (solo visualización)
    cambio_calculado = forms.DecimalField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'id': 'cambio-calculado'
        }),
        label="Cambio a entregar"
    )
    
    class Meta:
        model = Venta
        fields = ['metodo_pago', 'con_cuanto_paga', 'carrito_json', 'total_venta', 'cambio_calculado']
        widgets = {
            'metodo_pago': forms.Select(attrs={
                'class': 'form-control',
                'id': 'metodo-pago'
            }),
        }
        labels = {
            'metodo_pago': 'Método de Pago'
        }
    
    def __init__(self, *args, **kwargs):
        self.turno = kwargs.pop('turno', None)
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        # Agregar campo informativo del efectivo en caja (solo lectura)
        if self.turno:
            self.fields['efectivo_en_caja'] = forms.DecimalField(
                initial=self.turno.efectivo_final_en_caja(),
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': 'readonly',
                    'id': 'efectivo-en-caja'
                }),
                label="Efectivo disponible en caja"
            )

    def clean(self):
        cleaned_data = super().clean()
        metodo_pago = cleaned_data.get('metodo_pago')
        con_cuanto_paga = cleaned_data.get('con_cuanto_paga')
        carrito_json = cleaned_data.get('carrito_json')
        
        # Verificar que el carrito no esté vacío
        if not carrito_json or carrito_json == '[]':
            raise forms.ValidationError("No hay productos en el carrito de compras.")
            
        # Calcular el total a partir del carrito
        total = Decimal('0.00')
        try:
            carrito = json.loads(carrito_json)
            for item in carrito:
                subtotal = Decimal(str(item['subtotal']))
                total += subtotal
        except (json.JSONDecodeError, KeyError):
            raise forms.ValidationError("Error en el formato del carrito de compras.")
        
        # Validaciones para pagos en efectivo
        if metodo_pago and metodo_pago.es_efectivo:
            if con_cuanto_paga is None:
                raise forms.ValidationError({
                    'con_cuanto_paga': "Debes ingresar con cuánto paga el cliente."
                })
            if total and con_cuanto_paga < total:
                raise forms.ValidationError({
                    'con_cuanto_paga': "El monto entregado es menor al total de la venta."
                })
        
        # Verificar que exista turno activo
        if not self.turno or not self.turno.esta_activo():
            raise forms.ValidationError("No hay un turno activo. Debes iniciar un turno para realizar ventas.")
        
        # Guardar total calculado para usar en la vista
        self.total_calculado = total
        
        return cleaned_data
    
    def save(self, commit=True):
        """
        Sobrescribir el método save para manejar el carrito y el turno
        """
        venta = super().save(commit=False)
        
        # Asignar el usuario y el turno
        if self.usuario:
            venta.usuario = self.usuario
        
        if self.turno:
            venta.turno = self.turno
        
        # Asignar el total calculado
        venta.total = self.total_calculado
        
        # Calcular el cambio
        if venta.metodo_pago and venta.metodo_pago.es_efectivo and venta.con_cuanto_paga:
            venta.cambio = venta.calcular_cambio()
        
        if commit:
            venta.save()
        
        return venta


# -------------------- BASE FORMSET PERSONALIZADO --------------------

class BaseDetalleVentaFormSet(BaseInlineFormSet):
    """
    FormSet base personalizado para DetalleVenta
    """
    def clean(self):
        """
        Validación a nivel de formset
        """
        super().clean()
        
        # Verificar que al menos haya un producto
        if any(self.errors):
            return
            
        if not any(form.cleaned_data and not form.cleaned_data.get('DELETE', False)
                   for form in self.forms):
            raise forms.ValidationError("Debe agregar al menos un producto a la venta.")


# -------------------- FORMULARIO PARA AGREGAR DETALLES A LA VENTA --------------------

class DetalleVentaForm(forms.ModelForm):
    """
    Formulario para cada detalle de venta (cada producto en el carrito)
    """
    # Campo para búsqueda de productos (no parte del modelo)
    buscar_producto = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control buscar-producto-input',
            'placeholder': 'Buscar producto por nombre/código',
        }),
        label="Buscar producto"
    )
    
    class Meta:
        model = DetalleVenta
        fields = ['producto', 'lote', 'cantidad', 'precio_unitario', 'descuento_aplicado']
        widgets = {
            'producto': forms.Select(attrs={
                'class': 'form-control producto-select',
                'data-url': '/ventas/get-lotes-producto/'
            }),
            'lote': forms.Select(attrs={
                'class': 'form-control lote-select',
                'data-url': '/ventas/get-info-lote/'
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control cantidad-input',
                'min': '1',
                'value': '1',
                'placeholder': 'Cantidad'
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'class': 'form-control precio-unitario',
                'step': '0.01',
                'placeholder': 'Precio unitario',
                'readonly': 'readonly'
            }),
            'descuento_aplicado': forms.NumberInput(attrs={
                'class': 'form-control descuento-aplicado',
                'step': '0.01',
                'placeholder': 'Descuento',
                'readonly': 'readonly'
            }),
        }
        labels = {
            'producto': 'Producto',
            'lote': 'Lote',
            'cantidad': 'Cantidad',
            'precio_unitario': 'Precio Unitario',
            'descuento_aplicado': 'Descuento'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Limitar solo a productos activos
        self.fields['producto'].queryset = Producto.objects.filter(estado='activo')
        
        # Si hay un producto seleccionado, filtrar lotes
        instance = kwargs.get('instance')
        if instance and instance.producto_id:
            self.fields['lote'].queryset = InventarioProducto.objects.filter(
                producto=instance.producto,
                cantidad__gt=0
            )
        else:
            self.fields['lote'].queryset = InventarioProducto.objects.none()
            
        # Agregar campos de subtotal (solo visualización)
        self.fields['subtotal'] = forms.DecimalField(
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control subtotal-display',
                'readonly': 'readonly'
            }),
            label="Subtotal"
        )
    
    def clean(self):
        cleaned_data = super().clean()
        cantidad = cleaned_data.get('cantidad')
        lote = cleaned_data.get('lote')
        producto = cleaned_data.get('producto')
        
        if not producto:
            raise forms.ValidationError({
                'producto': "Debe seleccionar un producto."
            })
            
        if not lote:
            raise forms.ValidationError({
                'lote': "Debe seleccionar un lote."
            })
            
        if not cantidad or cantidad < 1:
            raise forms.ValidationError({
                'cantidad': "La cantidad debe ser al menos 1."
            })
            
        if lote and cantidad:
            if not lote.producto_id == producto.id_producto:
                raise forms.ValidationError({
                    'lote': "El lote seleccionado no corresponde al producto."
                })
                
            if cantidad > lote.cantidad:
                raise forms.ValidationError({
                    'cantidad': f"No hay suficiente stock en el lote seleccionado. Disponible: {lote.cantidad}"
                })
                
        # Asegurarse de que el precio y descuento coincidan con los del lote
        if lote:
            cleaned_data['precio_unitario'] = lote.precio_venta
            cleaned_data['descuento_aplicado'] = (lote.precio_venta * lote.descuento_porcentaje / 100) if lote.descuento_porcentaje else 0
        
        return cleaned_data


# -------------------- FORMSET PARA DETALLES DE VENTA --------------------

DetalleVentaFormSet = inlineformset_factory(
    Venta,
    DetalleVenta,
    form=DetalleVentaForm,
    formset=BaseDetalleVentaFormSet,
    extra=1,
    can_delete=True
)


# -------------------- FORMULARIO PARA CARRITO DE COMPRAS --------------------

class CarritoItemForm(forms.Form):
    """
    Formulario para manejar items individuales del carrito (no persistente)
    """
    producto_id = forms.IntegerField(widget=forms.HiddenInput())
    producto_nombre = forms.CharField(widget=forms.HiddenInput())
    lote_id = forms.IntegerField(widget=forms.HiddenInput())
    lote_codigo = forms.CharField(widget=forms.HiddenInput())
    cantidad = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    precio_unitario = forms.DecimalField(widget=forms.HiddenInput())
    descuento_aplicado = forms.DecimalField(widget=forms.HiddenInput())
    subtotal = forms.DecimalField(widget=forms.HiddenInput())
    
    class Meta:
        fields = ['producto_id', 'producto_nombre', 'lote_id', 'lote_codigo', 
                  'cantidad', 'precio_unitario', 'descuento_aplicado', 'subtotal']


# -------------------- FORMULARIO PARA BÚSQUEDA EN HISTORIAL DE VENTAS --------------------

class BusquedaVentasForm(forms.Form):
    """
    Formulario para filtrar ventas en el historial
    """
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label="Fecha inicio"
    )
    
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label="Fecha fin"
    )
    
    metodo_pago = forms.ModelChoiceField(
        queryset=MetodoPago.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label="Método de pago"
    )