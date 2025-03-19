from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.urls import reverse
from .forms import CustomUserCreationForm, CustomUserEditForm
from .models import PerfilUsuario

# ------------------------- AUTENTICACIÓN -------------------------

def user_login(request):
    """Autenticación de usuario con verificación de credenciales y asignación de roles."""
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_active:
                perfil = PerfilUsuario.objects.filter(usuario=user).first()

                if perfil:
                    login(request, user)
                    messages.success(request, f"Bienvenido, {user.username}.")
                    
                    return redirect(reverse('authapp:admin_dashboard' if perfil.rol == 'administrador' else 'authapp:vendedor_dashboard'))
                else:
                    messages.error(request, "Tu cuenta no tiene un perfil asociado. Contacta al administrador.")
            else:
                messages.error(request, "Tu cuenta está desactivada. Contacta al administrador.")
        else:
            messages.error(request, "⚠ Usuario o contraseña incorrectos. Inténtalo de nuevo.")

    return render(request, "login.html")

@login_required
def user_logout(request):
    """Cierre de sesión del usuario."""
    logout(request)
    messages.success(request, "Has cerrado sesión correctamente.")
    return redirect(reverse('authapp:login'))

# ------------------------- DASHBOARDS -------------------------

@login_required
def admin_dashboard(request):
    """Dashboard exclusivo para administradores."""
    perfil = PerfilUsuario.objects.filter(usuario=request.user).first()
    if not perfil or perfil.rol != 'administrador':
        messages.error(request, "Acceso denegado. No tienes permisos para esta sección.")
        return redirect(reverse('authapp:vendedor_dashboard'))
    return render(request, "admin_dashboard.html")

@login_required
def vendedor_dashboard(request):
    """Dashboard exclusivo para vendedores."""
    perfil = PerfilUsuario.objects.filter(usuario=request.user).first()
    if not perfil or perfil.rol != 'vendedor':
        messages.warning(request, "Los administradores no tienen acceso al panel de vendedores.")
        return redirect(reverse('authapp:admin_dashboard'))
    return render(request, "vendedor_dashboard.html")

# ------------------------- ADMINISTRACIÓN DE USUARIOS -------------------------

@login_required
@user_passes_test(lambda u: PerfilUsuario.objects.filter(usuario=u, rol="administrador").exists())
def admin_usuarios(request):
    """Lista de usuarios registrados (solo administradores)."""
    usuarios = User.objects.all()
    return render(request, "admin_usuarios.html", {"usuarios": usuarios})

@login_required
@user_passes_test(lambda u: PerfilUsuario.objects.filter(usuario=u, rol="administrador").exists())
def agregar_usuario(request):
    """Formulario para agregar un nuevo usuario."""
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f"Usuario {usuario.username} creado exitosamente.")
            return redirect(reverse("authapp:admin_usuarios"))
        else:
            messages.error(request, "Error al crear usuario. Revisa los datos ingresados.")
    else:
        form = CustomUserCreationForm()

    return render(request, "agregar_usuario.html", {"form": form})

@login_required
@user_passes_test(lambda u: PerfilUsuario.objects.filter(usuario=u, rol="administrador").exists())
def editar_usuario(request, usuario_id):
    """Formulario para editar la información de un usuario."""
    usuario = get_object_or_404(User, id=usuario_id)
    perfil = get_object_or_404(PerfilUsuario, usuario=usuario)

    if request.method == "POST":
        form = CustomUserEditForm(request.POST, instance=usuario)
        if form.is_valid():
            cambios_realizados = False

            # Verificar cambios en los campos del usuario
            campos_usuario = ["username", "first_name", "last_name", "email"]
            for campo in campos_usuario:
                if getattr(usuario, campo) != form.cleaned_data[campo]:
                    setattr(usuario, campo, form.cleaned_data[campo])
                    cambios_realizados = True

            # Verificar cambios en el rol
            if perfil.rol != form.cleaned_data["rol"]:
                perfil.rol = form.cleaned_data["rol"]
                cambios_realizados = True

            # Verificar cambio de contraseña
            nueva_password = form.cleaned_data["nueva_password1"]
            if nueva_password:
                usuario.set_password(nueva_password)
                cambios_realizados = True

            # Si no hubo cambios, mostrar mensaje
            if not cambios_realizados:
                messages.warning(request, "Debes modificar el rol o la contraseña para actualizar los cambios correctamente.")
                return redirect(reverse("authapp:editar_usuario", args=[usuario.id]))

            # Guardar cambios en usuario y perfil
            usuario.save()
            perfil.save()

            # Limpiar y reasignar grupos
            usuario.groups.clear()
            grupo, _ = Group.objects.get_or_create(name=perfil.rol)
            usuario.groups.add(grupo)

            messages.success(request, f"Usuario {usuario.username} actualizado exitosamente.")
            return redirect(reverse("authapp:admin_usuarios"))

        else:
            messages.error(request, "Error al actualizar usuario. Revisa los datos ingresados.")

    else:
        form = CustomUserEditForm(instance=usuario)

    return render(request, "editar_usuario.html", {"form": form, "usuario": usuario})

@login_required
@user_passes_test(lambda u: PerfilUsuario.objects.filter(usuario=u, rol="administrador").exists())
def eliminar_usuario(request, usuario_id):
    """Elimina un usuario de la base de datos (excepto superusuarios)."""
    usuario = get_object_or_404(User, id=usuario_id)

    if usuario.is_superuser:
        messages.error(request, "No puedes eliminar al usuario administrador principal.")
    else:
        usuario.delete()
        messages.success(request, f"Usuario {usuario.username} eliminado correctamente.")

    return redirect(reverse("authapp:admin_usuarios"))

# ------------------------- MÓDULOS ADICIONALES DEL ADMINISTRADOR -------------------------

@login_required
@user_passes_test(lambda u: PerfilUsuario.objects.filter(usuario=u, rol="administrador").exists())
def admin_inventario(request):
    return render(request, "admin_inventario.html")

@login_required
@user_passes_test(lambda u: PerfilUsuario.objects.filter(usuario=u, rol="administrador").exists())
def admin_reportes(request):
    return render(request, "admin_reportes.html")

@login_required
@user_passes_test(lambda u: PerfilUsuario.objects.filter(usuario=u, rol="administrador").exists())
def admin_proveedores(request):
    return render(request, "admin_proveedores.html")

@login_required
@user_passes_test(lambda u: PerfilUsuario.objects.filter(usuario=u, rol="administrador").exists())
def admin_soporte(request):
    return render(request, "admin_soporte.html")
