# Generated by Django 5.1.7 on 2025-03-22 00:11

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0011_alter_producto_codigo_barras'),
    ]

    operations = [
        migrations.AlterField(
            model_name='producto',
            name='codigo_barras',
            field=models.CharField(max_length=30, unique=True, validators=[django.core.validators.RegexValidator(message='El código de barras solo puede contener números.', regex='^[0-9]*$')]),
        ),
    ]
