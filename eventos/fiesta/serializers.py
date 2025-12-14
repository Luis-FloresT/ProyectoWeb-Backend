from rest_framework import serializers
from django.db import IntegrityError
from .models import ItemCarrito

from .models import (
    RegistroUsuario, Promocion, Categoria, Servicio, Combo, ComboServicio,
    HorarioDisponible, Reserva, DetalleReserva, Pago, Cancelacion
)


class RegistroUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroUsuario
        fields = ['id', 'nombre', 'apellido', 'telefono', 'email', 'fecha_registro', 'activo']
        read_only_fields = ['fecha_registro']


class PromocionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promocion
        fields = '__all__'


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'


class HorarioDisponibleSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorarioDisponible
        fields = '__all__'


class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = '__all__'
        read_only_fields = ['fecha_pago']


class CancelacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cancelacion
        fields = '__all__'
        read_only_fields = ['fecha_cancelacion']


class ComboServicioSerializer(serializers.ModelSerializer):
    servicio_nombre = serializers.CharField(source='servicio.nombre', read_only=True)

    class Meta:
        model = ComboServicio
        fields = ['combo', 'servicio', 'servicio_nombre', 'cantidad']


class DetalleReservaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleReserva
        fields = (
            'id',
            'reserva',
            'combo',
            'servicio',
            'tipo',
            'cantidad',
            'precio_unitario',
            'subtotal'
        )


class ServicioSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)

    class Meta:
        model = Servicio
        fields = '__all__'
        read_only_fields = ['fecha_creacion']


class ComboDetailSerializer(serializers.ModelSerializer):
    servicios_incluidos = ComboServicioSerializer(source='comboservicio_set', many=True, read_only=True)
    promocion_nombre = serializers.CharField(source='promocion.nombre', read_only=True)

    class Meta:
        model = Combo
        fields = '__all__'
        read_only_fields = ['fecha_creacion']


class ReservaSerializer(serializers.ModelSerializer):
    detalles = DetalleReservaSerializer(many=True, required=False)  # ← CORREGIDO
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)

    class Meta:
        model = Reserva
        fields = '__all__'
        read_only_fields = [
            'fecha_reserva',
            'cliente_nombre',
        ]

    def validate_codigo_reserva(self, value):
        if not value:
            raise serializers.ValidationError("El código de reserva no puede estar vacío.")
        return value

    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles', [])  # ← CORREGIDO

        try:
            reserva = Reserva.objects.create(**validated_data)
        except IntegrityError as e:
            if 'codigo_reserva' in str(e):
                raise serializers.ValidationError({"codigo_reserva": "Este código de reserva ya existe."})
            raise

        for detalle_data in detalles_data:
            DetalleReserva.objects.create(reserva=reserva, **detalle_data)

        return reserva

class ItemCarritoSerializer(serializers.ModelSerializer):
    servicio_id = serializers.IntegerField(write_only=True, required=False)
    combo_id = serializers.IntegerField(write_only=True, required=False)
    promocion_id = serializers.IntegerField(write_only=True, required=False)

    tipo = serializers.SerializerMethodField()

    class Meta:
        model = ItemCarrito
        fields = [
            'id',
            'servicio',
            'combo',
            'promocion',
            'servicio_id',
            'combo_id',
            'promocion_id',
            'cantidad',
            'activo',
            'fecha_agregado',
            'tipo'
        ]
        read_only_fields = ['servicio', 'combo', 'promocion', 'fecha_agregado']

    def get_tipo(self, obj):
        if obj.servicio:
            return "servicio"
        if obj.combo:
            return "combo"
        if obj.promocion:
            return "promocion"
        return None
    def create(self, validated_data):
        servicio_id = validated_data.pop('servicio_id', None)
        combo_id = validated_data.pop('combo_id', None)
        promocion_id = validated_data.pop('promocion_id', None)

        item = ItemCarrito.objects.create(**validated_data)

        if servicio_id:
            item.servicio_id = servicio_id
        if combo_id:
            item.combo_id = combo_id
        if promocion_id:
            item.promocion_id = promocion_id

        item.save()
        return item
