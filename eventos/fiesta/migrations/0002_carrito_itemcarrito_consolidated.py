# Generated migration - Consolidation of carrito and itemcarrito migrations
# This migration ensures the carrito structure is correct without breaking existing migrations

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fiesta', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Carrito',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('cliente', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='carrito', to='fiesta.registrousuario')),
            ],
            options={
                'verbose_name': 'Carrito de Compras',
                'verbose_name_plural': 'Carritos de Compras',
                'db_table': 'carrito',
            },
        ),
        migrations.CreateModel(
            name='ItemCarrito',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.PositiveIntegerField(default=1)),
                ('precio_unitario', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('carrito', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='fiesta.carrito')),
                ('combo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='fiesta.combo')),
                ('servicio', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='fiesta.servicio')),
            ],
            options={
                'verbose_name': 'Item del Carrito',
                'verbose_name_plural': 'Items del Carrito',
                'db_table': 'item_carrito',
            },
        ),
    ]
