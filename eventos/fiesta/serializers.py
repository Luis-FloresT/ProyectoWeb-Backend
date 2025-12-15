from rest_framework import serializers
from django.db import transaction, IntegrityError
from .models import (
    RegistroUsuario, Promocion, Categoria, Servicio, Combo, ComboServicio,
    HorarioDisponible, Reserva, DetalleReserva, Pago, Cancelacion,
    Carrito, ItemCarrito  # <--- Agregamos los nuevos modelos aquí
)

# ----------------- SERIALIZERS BÁSICOS -----------------

class RegistroUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroUsuario
        fields = ['id', 'nombre', 'apellido', 'telefono', 'email', 'fecha_registro', 'activo']
        read_only_fields = ['fecha_registro']

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class PromocionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promocion
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

# ----------------- SERIALIZERS RELACIONADOS -----------------

class ServicioSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)

    class Meta:
        model = Servicio
        fields = '__all__'
        read_only_fields = ['fecha_creacion']

class ComboServicioSerializer(serializers.ModelSerializer):
    servicio_nombre = serializers.CharField(source='servicio.nombre', read_only=True)

    class Meta:
        model = ComboServicio
        fields = ['combo', 'servicio', 'servicio_nombre', 'cantidad']

class ComboDetailSerializer(serializers.ModelSerializer):
    # Muestra los servicios dentro del combo al consultarlo
    servicios_incluidos = ComboServicioSerializer(source='comboservicio_set', many=True, read_only=True)
    promocion_nombre = serializers.CharField(source='promocion.nombre', read_only=True)

    class Meta:
        model = Combo
        fields = '__all__'
        read_only_fields = ['fecha_creacion']

# ----------------- SERIALIZERS CARRITO (NUEVO) -----------------

class ItemCarritoSerializer(serializers.ModelSerializer):
    # Campos calculados para facilitar el trabajo al Frontend
    nombre_producto = serializers.SerializerMethodField()
    imagen_producto = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = ItemCarrito
        fields = ['id', 'servicio', 'combo', 'cantidad', 'precio_unitario', 'subtotal', 'nombre_producto', 'imagen_producto']

    def get_nombre_producto(self, obj):
        if obj.servicio: return obj.servicio.nombre
        if obj.combo: return obj.combo.nombre
        return "Producto Desconocido"

    def get_imagen_producto(self, obj):
        if obj.servicio and obj.servicio.imagen: return obj.servicio.imagen
        if obj.combo and obj.combo.imagen: return obj.combo.imagen
        return None

class CarritoSerializer(serializers.ModelSerializer):
    items = ItemCarritoSerializer(many=True, read_only=True)
    total_carrito = serializers.SerializerMethodField()

    class Meta:
        model = Carrito
        fields = ['id', 'cliente', 'items', 'total_carrito', 'actualizado_en']

    def get_total_carrito(self, obj):
        # Suma todos los subtotales de los items en el carrito
        return sum(item.subtotal for item in obj.items.all())

# ----------------- SERIALIZER COMPLEJO (RESERVA) -----------------

class DetalleReservaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleReserva
        fields = [
            'id', 'reserva', 'tipo', 'combo', 'servicio',
            'cantidad', 'precio_unitario', 'subtotal'
        ]
        read_only_fields = ['reserva'] # La reserva se asigna automáticamente

class ReservaSerializer(serializers.ModelSerializer):
    # Permite enviar detalles anidados al crear
    detalles = DetalleReservaSerializer(many=True, required=False)
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)

    class Meta:
        model = Reserva
        fields = '__all__'
        read_only_fields = ['fecha_reserva', 'cliente_nombre']

    def validate_codigo_reserva(self, value):
        if not value:
            raise serializers.ValidationError("El código de reserva no puede estar vacío.")
        if Reserva.objects.filter(codigo_reserva=value).exists():
             raise serializers.ValidationError("Este código de reserva ya existe.")
        return value

    def create(self, validated_data):
        # Extraemos los detalles para guardarlos aparte
        detalles_data = validated_data.pop('detalles', [])
        
        # Usamos una transacción para asegurar integridad de datos
        with transaction.atomic():
            reserva = Reserva.objects.create(**validated_data)
            
            for detalle in detalles_data:
                DetalleReserva.objects.create(reserva=reserva, **detalle)
                
        return reserva