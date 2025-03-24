from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test





def es_vendedor(user):
    return user.is_authenticated and user.groups.filter(name='vendedor').exists()


# -------------------- VISTA PRINCIPAL --------------------

@login_required
@user_passes_test(es_vendedor)
def registro_venta(request):
    return render(request, 'registro_venta.html')
