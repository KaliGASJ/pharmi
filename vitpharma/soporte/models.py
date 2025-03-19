from django.db import models
class TicketSoporte(models.Model):
    id_ticket = models.AutoField(primary_key=True)
    usuario = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=[('Abierto', 'Abierto'), ('Cerrado', 'Cerrado')], default='Abierto')
    descripcion = models.TextField()

    def __str__(self):
        return f"Ticket {self.id_ticket} - {self.estado}"

