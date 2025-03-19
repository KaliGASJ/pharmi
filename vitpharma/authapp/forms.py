from django import forms
from django.contrib.auth.models import User, Group
from .models import PerfilUsuario

# -------------------- FORMULARIO DE REGISTRO --------------------

class CustomUserCreationForm(forms.ModelForm):
    ROLES = [
        ('administrador', 'Administrador'),
        ('vendedor', 'Vendedor'),
    ]
    
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput, required=True)
    password2 = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput, required=True)
    rol = forms.ChoiceField(choices=ROLES, label="Rol del Usuario", required=True)
    
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def clean_password2(self):
        """Verifica que las contraseñas coincidan"""
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return password2

    def save(self, commit=True):
        """Guarda el usuario con su perfil y rol asignado"""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        
        if commit:
            user.save()
            perfil = PerfilUsuario.objects.create(usuario=user, rol=self.cleaned_data["rol"])
            grupo, _ = Group.objects.get_or_create(name=self.cleaned_data["rol"])
            user.groups.add(grupo)
        
        return user

# -------------------- FORMULARIO DE EDICIÓN --------------------

class CustomUserEditForm(forms.ModelForm):
    telefono = forms.CharField(max_length=15, required=False, label="Teléfono")
    direccion = forms.CharField(widget=forms.Textarea, required=False, label="Dirección")
    imagen_perfil = forms.ImageField(required=False, label="Imagen de Perfil")
    rol = forms.ChoiceField(choices=CustomUserCreationForm.ROLES, label="Rol del Usuario", required=True)

    # Nueva opción para cambiar la contraseña
    nueva_password1 = forms.CharField(label="Nueva Contraseña", widget=forms.PasswordInput, required=False)
    nueva_password2 = forms.CharField(label="Confirmar Nueva Contraseña", widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def clean(self):
        """Verifica si las contraseñas coinciden y si hay cambios"""
        cleaned_data = super().clean()
        password1 = cleaned_data.get("nueva_password1")
        password2 = cleaned_data.get("nueva_password2")

        if password1 or password2:
            if not password1 or not password2:
                self.add_error("nueva_password2", "Debes ingresar y confirmar la nueva contraseña.")
            elif password1 != password2:
                self.add_error("nueva_password2", "Las contraseñas no coinciden.")

        # Verificar si hay cambios en los campos del usuario
        usuario = self.instance
        cambios_realizados = False

        for campo in ["username", "first_name", "last_name", "email"]:
            if getattr(usuario, campo) != cleaned_data.get(campo):
                cambios_realizados = True

        perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)

        for campo in ["telefono", "direccion", "rol"]:
            if getattr(perfil, campo) != cleaned_data.get(campo):
                cambios_realizados = True

        if not cambios_realizados and not password1:
            raise forms.ValidationError("Debes modificar al menos un campo para actualizar el usuario.")

    def save(self, commit=True):
        """Guarda los cambios en el usuario"""
        user = super().save(commit=False)

        if self.cleaned_data["nueva_password1"]:
            user.set_password(self.cleaned_data["nueva_password1"])

        if commit:
            user.save()
            perfil, _ = PerfilUsuario.objects.get_or_create(usuario=user)

            perfil.telefono = self.cleaned_data["telefono"]
            perfil.direccion = self.cleaned_data["direccion"]
            perfil.rol = self.cleaned_data["rol"]

            if self.cleaned_data.get("imagen_perfil"):
                perfil.imagen_perfil = self.cleaned_data["imagen_perfil"]

            perfil.save()

            user.groups.clear()
            grupo, _ = Group.objects.get_or_create(name=self.cleaned_data["rol"])
            user.groups.add(grupo)

        return user
