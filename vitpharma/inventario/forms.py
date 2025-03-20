from django import forms
from .models import Producto, InventarioProducto, Proveedor


# -------------------- FORMULARIO DE REGISTRO Y EDICIÓN DE PRODUCTOS --------------------

class ProductoForm(forms.ModelForm):
    """Formulario para registrar y editar productos"""

    class Meta:
        model = Producto
        fields = [
            "nombre", "descripcion", "id_categoria", "id_departamento", "codigo_barras",
            "stock_minimo"
        ]
        labels = {
            "nombre": "Nombre del Producto",
            "descripcion": "Descripción",
            "id_categoria": "Categoría",
            "id_departamento": "Departamento",
            "codigo_barras": "Código de Barras",
            "stock_minimo": "Stock Mínimo"
        }
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3, "class": "form-control", "placeholder": "Ingrese la descripción del producto"}),
            "codigo_barras": forms.TextInput(attrs={"class": "form-control", "placeholder": "Escanee o ingrese el código de barras"}),
            "stock_minimo": forms.NumberInput(attrs={"min": 1, "class": "form-control"}),
        }

    def clean_codigo_barras(self):
        """Verifica que el código de barras sea único y solo contenga números."""
        codigo_barras = self.cleaned_data.get("codigo_barras")
        if codigo_barras and not codigo_barras.isdigit():
            raise forms.ValidationError("El código de barras solo puede contener números.")
        if Producto.objects.exclude(pk=self.instance.pk).filter(codigo_barras=codigo_barras).exists():
            raise forms.ValidationError("Ya existe un producto con este código de barras.")
        return codigo_barras


# -------------------- FORMULARIO PARA AGREGAR LOTES --------------------

class AgregarLoteForm(forms.ModelForm):
    """Formulario para agregar nuevos lotes de productos en el inventario"""

    id_proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.all(),
        required=True,
        label="Proveedor",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    class Meta:
        model = InventarioProducto
        fields = [
            "producto", "lote", "id_proveedor", "fecha_caducidad",
            "precio_compra", "precio_venta", "cantidad", "descuento_porcentaje"
        ]
        labels = {
            "producto": "Producto",
            "lote": "Número de Lote",
            "id_proveedor": "Proveedor",
            "fecha_caducidad": "Fecha de Caducidad",
            "precio_compra": "Precio de Compra",
            "precio_venta": "Precio de Venta",
            "cantidad": "Cantidad",
            "descuento_porcentaje": "Descuento (%)"
        }
        widgets = {
            "producto": forms.Select(attrs={"class": "form-control"}),
            "lote": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ingrese el número de lote"}),
            "fecha_caducidad": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "cantidad": forms.NumberInput(attrs={"min": 1, "class": "form-control"}),
            "descuento_porcentaje": forms.NumberInput(attrs={"step": "0.01", "min": "0", "class": "form-control"}),
            "precio_compra": forms.NumberInput(attrs={"step": "0.01", "min": "0", "class": "form-control"}),
            "precio_venta": forms.NumberInput(attrs={"step": "0.01", "min": "0", "class": "form-control"}),
        }


# -------------------- FORMULARIO PARA AGREGAR STOCK --------------------

class AgregarStockForm(forms.ModelForm):
    """Formulario para agregar stock a un lote existente"""

    id_proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.all(),
        required=True,
        label="Proveedor",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    class Meta:
        model = InventarioProducto
        fields = [
            "producto", "lote", "id_proveedor", "cantidad"
        ]
        labels = {
            "producto": "Producto",
            "lote": "Número de Lote",
            "id_proveedor": "Proveedor",
            "cantidad": "Cantidad a Agregar"
        }
        widgets = {
            "producto": forms.Select(attrs={"class": "form-control"}),
            "lote": forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "cantidad": forms.NumberInput(attrs={"min": 1, "class": "form-control"}),
        }


# -------------------- FORMULARIO PARA EDITAR UN LOTE --------------------

class EditarLoteForm(forms.ModelForm):
    """Formulario para editar un lote existente"""

    id_proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.all(),
        required=True,
        label="Proveedor",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    class Meta:
        model = InventarioProducto
        fields = [
            "lote", "id_proveedor", "fecha_caducidad",
            "precio_compra", "precio_venta", "cantidad", "descuento_porcentaje"
        ]
        labels = {
            "lote": "Número de Lote",
            "id_proveedor": "Proveedor",
            "fecha_caducidad": "Fecha de Caducidad",
            "precio_compra": "Precio de Compra",
            "precio_venta": "Precio de Venta",
            "cantidad": "Cantidad Disponible",
            "descuento_porcentaje": "Descuento (%)"
        }
        widgets = {
            "lote": forms.TextInput(attrs={"class": "form-control"}),
            "fecha_caducidad": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "precio_compra": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "precio_venta": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "descuento_porcentaje": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "100"}),
        }

    def clean(self):
        """Validaciones antes de actualizar el lote"""
        cleaned_data = super().clean()
        cantidad = cleaned_data.get("cantidad")
        precio_compra = cleaned_data.get("precio_compra")
        precio_venta = cleaned_data.get("precio_venta")

        if cantidad is None or cantidad < 0:
            self.add_error("cantidad", "La cantidad debe ser mayor o igual a cero.")

        if precio_venta is not None and precio_compra is not None and precio_venta < precio_compra:
            self.add_error("precio_venta", "El precio de venta no puede ser menor al precio de compra.")

        return cleaned_data


# -------------------- FORMULARIO PARA ELIMINAR UN LOTE --------------------

class EliminarLoteForm(forms.Form):
    """Formulario para confirmar la eliminación de un lote"""
    confirmacion = forms.BooleanField(
        required=True,
        label="Confirmo que deseo eliminar este lote"
    )
