from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from .models import Venta, DetalleVenta, MetodoPago
from inventario.models import InventarioProducto, Producto

class VentaForm(forms.ModelForm):
    """Formulario para el registro de ventas"""
    
    class Meta:
        model = Venta
        fields = ['metodo_pago']
        widgets = {
            'metodo_pago': forms.Select(attrs={
                'class': 'form-control',
                'id': 'metodo-pago-select'
            })
        }

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        self.turno = kwargs.pop('turno', None)
        super().__init__(*args, **kwargs)
        
        # Personalizar el campo de método de pago
        self.fields['metodo_pago'].label = "Método de Pago"
        self.fields['metodo_pago'].empty_label = "Seleccione un método de pago"
        self.fields['metodo_pago'].required = True
        
        # Si estamos en modo de edición, no permitir cambiar algunos campos
        if self.instance and self.instance.pk:
            # Los campos de solo lectura dependen de si la venta ya ha sido procesada
            if self.instance.generado_ticket:
                self.fields['metodo_pago'].disabled = True
        
    def clean(self):
        cleaned_data = super().clean()
        
        # Si no hay un turno activo, mostrar error
        if not self.turno or not self.turno.esta_activo:
            raise ValidationError("No hay un turno activo. Debe iniciar un turno para realizar ventas.")
            
        return cleaned_data
        
    def save(self, commit=True):
        venta = super().save(commit=False)
        
        if self.usuario:
            venta.usuario = self.usuario
            # Guardar el usuario como usuario_registro si es nuevo
            if not venta.pk:
                venta.usuario_registro = self.usuario
            else:
                # En edición, guardar como usuario_modificacion
                venta.usuario_modificacion = self.usuario
        
        if self.turno:
            venta.turno = self.turno
            
        if commit:
            venta.save()
            
        return venta

class DetalleVentaForm(forms.ModelForm):
    """Formulario para cada ítem dentro de una venta"""
    
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(estado='activo'),
        label="Producto",
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control producto-select',
            'placeholder': 'Buscar producto...'
        })
    )
    
    lote = forms.ModelChoiceField(
        queryset=InventarioProducto.objects.filter(cantidad__gt=0),
        label="Lote",
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control lote-select',
            'placeholder': 'Seleccionar lote'
        })
    )
    
    class Meta:
        model = DetalleVenta
        fields = ['lote_vendido', 'cantidad', 'precio_unitario', 'descuento_unitario']
        widgets = {
            'lote_vendido': forms.HiddenInput(),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control cantidad-input',
                'min': '1',
                'step': '1',
                'placeholder': 'Cantidad'
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'step': '0.01'
            }),
            'descuento_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'step': '0.01'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Inicialmente el queryset de lotes estará vacío hasta que se seleccione un producto
        self.fields['lote'].queryset = InventarioProducto.objects.none()
        
        # Si ya existe una instancia, pre-seleccionar el producto
        if self.instance and self.instance.pk and self.instance.lote_vendido:
            producto = self.instance.lote_vendido.producto
            self.fields['producto'].initial = producto
            self.fields['lote'].queryset = InventarioProducto.objects.filter(
                producto=producto,
                cantidad__gt=0
            )
            self.fields['lote'].initial = self.instance.lote_vendido
            
            # Si la venta ya está procesada, deshabilitar edición
            venta = self.instance.venta
            if venta and venta.generado_ticket:
                for field_name in self.fields:
                    self.fields[field_name].disabled = True
    
    def clean(self):
        cleaned_data = super().clean()
        lote = cleaned_data.get('lote')
        cantidad = cleaned_data.get('cantidad')
        
        if lote and cantidad:
            # Verificar stock disponible
            if lote.cantidad < cantidad:
                raise ValidationError({
                    'cantidad': f"Stock insuficiente. Disponible: {lote.cantidad}"
                })
                
            # Asignar el precio unitario y descuento automáticamente
            cleaned_data['precio_unitario'] = lote.precio_venta
            cleaned_data['descuento_unitario'] = (lote.precio_venta * lote.descuento_porcentaje / 100) if lote.descuento_porcentaje else 0
            
            # Asignar el lote vendido
            cleaned_data['lote_vendido'] = lote
        
        return cleaned_data
    
    def save(self, commit=True):
        detalle = super().save(commit=False)
        
        # Asegurarse de que se calcule el subtotal si no se ha hecho
        if not detalle.subtotal or detalle.subtotal == 0:
            detalle.calcular_subtotal()
            
        if commit:
            detalle.save()
            
        return detalle

# FormSet para manejar múltiples ítems de venta
DetalleVentaFormSet = inlineformset_factory(
    Venta, 
    DetalleVenta,
    form=DetalleVentaForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)

class MetodoPagoForm(forms.ModelForm):
    """Formulario para administrar métodos de pago"""
    
    class Meta:
        model = MetodoPago
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del método de pago'
            })
        }
        
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if nombre:
            # Validar que no exista otro método de pago con este nombre
            if MetodoPago.objects.filter(nombre__iexact=nombre).exclude(id=self.instance.id if self.instance else None).exists():
                raise ValidationError("Ya existe un método de pago con este nombre")
            return nombre
        return nombre