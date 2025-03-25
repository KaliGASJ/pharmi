from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test


# Verifica si el usuario pertenece al grupo "vendedor"
def es_vendedor(user):
    return user.is_authenticated and user.groups.filter(name='vendedor').exists()

@login_required
@user_passes_test(es_vendedor)
def turno_dashboard(request):
    return render(request, 'turno_dashboard.html')
    
