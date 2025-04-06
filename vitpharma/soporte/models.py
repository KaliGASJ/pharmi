from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now

class Conversacion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversaciones')
    pregunta = models.TextField(verbose_name='Pregunta del usuario')
    respuesta = models.TextField(verbose_name='Respuesta del chatbot')
    fecha = models.DateTimeField(default=now, verbose_name='Fecha de la conversación')

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Conversación'
        verbose_name_plural = 'Conversaciones'

    def __str__(self):
        return f"[{self.fecha.strftime('%Y-%m-%d %H:%M')}] {self.usuario.username}: {self.pregunta[:50]}"
