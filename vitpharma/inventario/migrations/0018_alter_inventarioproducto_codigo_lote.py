# Generated by Django 5.1.7 on 2025-03-25 02:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0017_alter_inventarioproducto_codigo_lote'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inventarioproducto',
            name='codigo_lote',
            field=models.CharField(default='LOTE-TEMP', max_length=30, unique=True),
            preserve_default=False,
        ),
    ]
