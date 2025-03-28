# Generated by Django 5.1.7 on 2025-03-25 04:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0007_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='cambio',
            field=models.DecimalField(decimal_places=2, default=0.0, help_text='Cambio devuelto al cliente (solo efectivo)', max_digits=10),
        ),
        migrations.AddField(
            model_name='venta',
            name='con_cuanto_paga',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Solo se usa si el método de pago es en efectivo', max_digits=10, null=True),
        ),
    ]
