from django import forms
from inventario.models import Producto, InventarioProducto, Categoria, Departamento, Proveedor

class ProductoVendedorForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'nombre',
            'descripcion',
            'id_categoria',
            'id_departamento',
            'stock_minimo',
            'codigo_barras',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'id_categoria': forms.Select(attrs={'class': 'form-control'}),
            'id_departamento': forms.Select(attrs={'class': 'form-control'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control'}),
            'codigo_barras': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        instance.estado = "inactivo"  # Forzar estado inicial
        if user:
            instance.usuario_registro = user
            instance.usuario_modificacion = user
        if commit:
            instance.save()
        return instance
    

class LoteVendedorForm(forms.ModelForm):
    class Meta:
        model = InventarioProducto
        fields = [
            'producto',
            'lote',
            'id_proveedor',
            'fecha_caducidad',
            'precio_compra',
            'precio_venta',
            'cantidad',
            'descuento_porcentaje',
        ]
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-control'}),
            'lote': forms.TextInput(attrs={'class': 'form-control'}),
            'id_proveedor': forms.Select(attrs={'class': 'form-control'}),
            'fecha_caducidad': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'precio_compra': forms.NumberInput(attrs={'class': 'form-control'}),
            'precio_venta': forms.NumberInput(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'descuento_porcentaje': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if user:
            instance.usuario_registro = user
            instance.usuario_modificacion = user
        if commit:
            instance.save()
        return instance
    
    