from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

def es_vendedor(user):
    return user.groups.filter(name='vendedor').exists()

@login_required
@user_passes_test(es_vendedor)
def reportes_inicio(request):
    return render(request, 'reportes_inicio.html')
