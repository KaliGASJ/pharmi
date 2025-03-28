# Generated by Django 5.1.7 on 2025-03-23 18:31

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('inventario', '0014_producto_estado'),
        ('turnos', '0001_initial'),
        ('ventas', '0002_remove_venta_metodo_pago_remove_venta_vendedor_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MetodoPago',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('nombre', models.CharField(max_length=40, unique=True)),
            ],
            options={
                'verbose_name': 'Método de pago',
                'verbose_name_plural': 'Métodos de pago',
            },
        ),
        migrations.CreateModel(
            name='Venta',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('fecha_hora', models.DateTimeField(auto_now_add=True)),
                ('total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('generado_ticket', models.BooleanField(default=False)),
                ('archivo_ticket', models.FileField(blank=True, null=True, upload_to='tickets/')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('modificado_en', models.DateTimeField(auto_now=True)),
                ('metodo_pago', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='ventas.metodopago')),
                ('turno', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ventas', to='turnos.turno')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ventas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Venta',
                'verbose_name_plural': 'Ventas',
                'ordering': ['-fecha_hora'],
            },
        ),
        migrations.CreateModel(
            name='DetalleVenta',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('cantidad', models.PositiveIntegerField()),
                ('precio_unitario', models.DecimalField(decimal_places=2, max_digits=10)),
                ('descuento_unitario', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('total_descuento', models.DecimalField(decimal_places=2, default=0.0, help_text='Total descontado = cantidad * descuento_unitario', max_digits=10)),
                ('subtotal', models.DecimalField(decimal_places=2, help_text='Total = (precio_unitario * cantidad) - total_descuento', max_digits=10)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('lote_vendido', models.ForeignKey(help_text='Lote específico del producto vendido', on_delete=django.db.models.deletion.PROTECT, related_name='detalles_venta', to='inventario.inventarioproducto')),
                ('venta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detalles', to='ventas.venta')),
            ],
            options={
                'verbose_name': 'Detalle de venta',
                'verbose_name_plural': 'Detalles de venta',
            },
        ),
    ]
