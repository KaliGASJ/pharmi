from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from weasyprint import HTML


# -------------------- VERIFICADOR DE ROL --------------------

def es_vendedor(user):
    return user.is_authenticated and user.groups.filter(name='vendedor').exists()


# -------------------- DASHBOARD DEL MÓDULO DE TURNOS --------------------

@login_required
@user_passes_test(es_vendedor)
def turno_dashboard(request):
    
    
    return render(request, 'turno_dashboard.html')


