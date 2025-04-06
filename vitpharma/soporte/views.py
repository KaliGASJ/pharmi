import os
import requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import PreguntaForm
from .models import Conversacion

@login_required
def chatbot_view(request):
    conversaciones = Conversacion.objects.filter(usuario=request.user).order_by('-fecha')[:10]
    respuesta = None

    if request.method == 'POST':
        form = PreguntaForm(request.POST)
        if form.is_valid():
            pregunta = form.cleaned_data['pregunta']

            headers = {
                "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"
            }

            # ✅ Obtener el rol real desde PerfilUsuario
            try:
                perfil = request.user.perfil
                rol_usuario = perfil.rol  # 'admin' o 'vendedor'
            except:
                rol_usuario = 'vendedor'  # fallback si no tiene perfil

            # ✅ Asignar archivo según rol
            if rol_usuario == 'admin':
                nombre_archivo = 'prompt_context_admin.txt'
            else:
                nombre_archivo = 'prompt_context_vendedor.txt'

            # ✅ Cargar contexto desde archivo externo
            try:
                ruta_contexto = os.path.join(settings.BASE_DIR, nombre_archivo)
                with open(ruta_contexto, 'r', encoding='utf-8') as f:
                    contexto = f.read()
            except FileNotFoundError:
                contexto = (
                    "Eres un asistente técnico de VITPHARMA. No se pudo cargar el contexto completo. "
                    "Responde de forma clara, breve y profesional."
                )

            # Construcción del input para la API
            data = {
                "inputs": f"{contexto}\n\nUsuario: {pregunta}\n\nAsistente:"
            }

            try:
                res = requests.post(
                    "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1",
                    headers=headers,
                    json=data,
                    timeout=25
                )
                res.raise_for_status()
                output = res.json()

                # Extraer respuesta sin repetir el contexto
                generated = output[0].get("generated_text", "")
                respuesta = generated.replace(data["inputs"], "").strip()

                Conversacion.objects.create(
                    usuario=request.user,
                    pregunta=pregunta,
                    respuesta=respuesta
                )

                return redirect('soporte:chatbot_view')

            except Exception as e:
                import traceback
                traceback.print_exc()
                respuesta = f"Bot: Error al conectar con el asistente: {str(e)}"
    else:
        form = PreguntaForm()

    return render(request, 'chatbot.html', {
        'form': form,
        'conversaciones': conversaciones,
        'respuesta': respuesta
    })
