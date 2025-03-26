from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from weasyprint import HTML
# -------------------- VERIFICAR SI ES VENDEDOR --------------------

def es_vendedor(user):
    return user.is_authenticated and user.groups.filter(name='vendedor').exists()


# -------------------- DASHBOARD DE REGISTRO DE VENTAS --------------------

@login_required
@user_passes_test(es_vendedor)
def venta_dashboard(request):
    
    return render(request, 'venta_dashboard.html')


