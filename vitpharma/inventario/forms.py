from django import forms
from .models import Producto, InventarioProducto, Proveedor

# -------------------- FORMULARIO DE REGISTRO DE PRODUCTOS --------------------

class ProductoForm(forms.ModelForm):
    """Formulario para que el administrador agregue un nuevo producto."""
    
    class Meta:
        model = Producto
        fields = ["nombre", "descripcion", "id_categoria", "id_departamento", "codigo_barras", "estado"]
        labels = {
            "nombre": "Nombre del Producto",
            "descripcion": "Descripción",
            "id_categoria": "Categoría",
            "id_departamento": "Departamento",
            "codigo_barras": "Código de Barras",
            "estado": "Estado (Activo/Inactivo)"
        }
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3, "placeholder": "Ingrese la descripción del producto...", "class": "form-control"}),
            "codigo_barras": forms.TextInput(attrs={"placeholder": "Escanee o ingrese el código de barras", "class": "form-control"}),
        }

    def clean_nombre(self):
        """Evita nombres duplicados ignorando mayúsculas y espacios extra."""
        nombre = self.cleaned_data.get("nombre").strip()
        if Producto.objects.filter(nombre__iexact=nombre).exists():
            raise forms.ValidationError("Ya existe un producto con este nombre. Verifique antes de agregarlo.")
        return nombre

# -------------------- FORMULARIO DE GESTIÓN DE INVENTARIO --------------------

class InventarioProductoForm(forms.ModelForm):
    """Formulario para agregar o actualizar lotes de productos en el inventario."""

    id_proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.all(),
        required=False,
        label="Proveedor",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    class Meta:
        model = InventarioProducto
        fields = ["producto", "lote", "id_proveedor", "fecha_caducidad",
                  "precio_compra", "precio_venta", "cantidad", "descuento_porcentaje"]
        labels = {
            "producto": "Producto",
            "lote": "Número de Lote",
            "id_proveedor": "Proveedor",
            "fecha_caducidad": "Fecha de Caducidad",
            "precio_compra": "Precio de Compra",
            "precio_venta": "Precio de Venta",
            "cantidad": "Cantidad a Agregar",
            "descuento_porcentaje": "Descuento (%)",
        }
        widgets = {
            "producto": forms.Select(attrs={"class": "form-control"}),
            "lote": forms.TextInput(attrs={"placeholder": "Ingrese el número de lote", "class": "form-control"}),
            "fecha_caducidad": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "cantidad": forms.NumberInput(attrs={"min": 1, "class": "form-control"}),
            "descuento_porcentaje": forms.NumberInput(attrs={"step": "0.01", "min": "0", "class": "form-control"}),
            "precio_compra": forms.NumberInput(attrs={"step": "0.01", "min": "0", "class": "form-control"}),
            "precio_venta": forms.NumberInput(attrs={"step": "0.01", "min": "0", "class": "form-control"}),
        }

    def clean(self):
        """Validaciones adicionales antes de guardar el formulario."""
        cleaned_data = super().clean()
        lote = cleaned_data.get("lote")
        producto = cleaned_data.get("producto")
        id_proveedor = cleaned_data.get("id_proveedor")
        cantidad = cleaned_data.get("cantidad")
        precio_compra = cleaned_data.get("precio_compra")
        precio_venta = cleaned_data.get("precio_venta")

        if not producto:
            raise forms.ValidationError("Debe seleccionar un producto válido.")

        if cantidad and cantidad <= 0:
            self.add_error("cantidad", "La cantidad debe ser mayor a cero.")

        if precio_venta and precio_compra and precio_venta < precio_compra:
            self.add_error("precio_venta", "El precio de venta no puede ser menor al precio de compra.")

        if lote and InventarioProducto.objects.filter(producto=producto, lote=lote, id_proveedor=id_proveedor).exists():
            self.add_error("lote", "Este número de lote ya existe para el mismo producto y proveedor.")

        return cleaned_data

# -------------------- FORMULARIO PARA VENDEDORES (Agregar stock) --------------------

class AgregarStockForm(forms.ModelForm):
    """Formulario exclusivo para que los vendedores agreguen más stock a productos existentes."""
    
    id_proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.all(),
        required=False,
        label="Proveedor",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    class Meta:
        model = InventarioProducto
        fields = ["producto", "lote", "id_proveedor", "fecha_caducidad", "cantidad"]
        labels = {
            "producto": "Producto",
            "lote": "Número de Lote",
            "id_proveedor": "Proveedor",
            "fecha_caducidad": "Fecha de Caducidad",
            "cantidad": "Cantidad a Agregar",
        }
        widgets = {
            "producto": forms.Select(attrs={"class": "form-control"}),
            "lote": forms.TextInput(attrs={"placeholder": "Ingrese el número de lote", "class": "form-control"}),
            "fecha_caducidad": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "cantidad": forms.NumberInput(attrs={"min": 1, "class": "form-control"}),
        }

    def clean(self):
        """Verificaciones adicionales antes de agregar stock."""
        cleaned_data = super().clean()
        cantidad = cleaned_data.get("cantidad")
        lote = cleaned_data.get("lote")
        producto = cleaned_data.get("producto")
        id_proveedor = cleaned_data.get("id_proveedor")

        if not producto:
            raise forms.ValidationError("Debe seleccionar un producto válido.")

        if cantidad and cantidad <= 0:
            self.add_error("cantidad", "La cantidad debe ser mayor a cero.")

        if lote and InventarioProducto.objects.filter(producto=producto, lote=lote, id_proveedor=id_proveedor).exists():
            self.add_error("lote", "Este número de lote ya existe para el mismo producto y proveedor. Si es una reposición, use el formulario de edición de inventario.")

        return cleaned_data
