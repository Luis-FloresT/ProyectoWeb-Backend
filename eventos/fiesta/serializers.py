from rest_framework import serializers
from django.db import transaction, IntegrityError
from .models import (
    RegistroUsuario, Promocion, Categoria, Servicio, Combo, ComboServicio,
    HorarioDisponible, Reserva, DetalleReserva, Pago, Cancelacion,
    Carrito, ItemCarrito, ConfiguracionPago  # <--- Agregamos los nuevos modelos aquí
)

# ----------------- SERIALIZERS BÁSICOS -----------------

class RegistroUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroUsuario
        fields = ['id', 'nombre', 'apellido', 'telefono', 'email', 'activo']

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

class ConfiguracionPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionPago
        fields = '__all__'

class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = '__all__'

class CancelacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cancelacion
        fields = '__all__'

# ----------------- SERIALIZERS RELACIONADOS -----------------

class ServicioSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)

    class Meta:
        model = Servicio
        fields = '__all__'

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

# ----------------- SERIALIZERS CARRITO (NUEVO) -----------------

class ItemCarritoSerializer(serializers.ModelSerializer):
    # Campos calculados para facilitar el trabajo al Frontend
    nombre_producto = serializers.SerializerMethodField()
    imagen_producto = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = ItemCarrito
        fields = ['id', 'servicio', 'combo', 'promocion', 'cantidad', 'precio_unitario', 'subtotal', 'nombre_producto', 'imagen_producto']

    def get_nombre_producto(self, obj):
        if obj.servicio: return obj.servicio.nombre
        if obj.combo: return obj.combo.nombre
        if obj.promocion: return obj.promocion.nombre
        return "Producto Desconocido"

    def get_imagen_producto(self, obj):
        if obj.servicio and obj.servicio.imagen: return obj.servicio.imagen
        if obj.combo and obj.combo.imagen: return obj.combo.imagen
        # Las promociones podrían no tener imagen propia, se puede asignar una por defecto o None
        return None

class CarritoSerializer(serializers.ModelSerializer):
    items = ItemCarritoSerializer(many=True, read_only=True)
    total_carrito = serializers.SerializerMethodField()

    class Meta:
        model = Carrito
        fields = ['id', 'cliente', 'items', 'total_carrito']

    def get_total_carrito(self, obj):
        # Suma todos los subtotales de los items en el carrito
        return sum(item.subtotal for item in obj.items.all())

# ----------------- SERIALIZER COMPLEJO (RESERVA) -----------------

class DetalleReservaSerializer(serializers.ModelSerializer):
    nombre_item = serializers.SerializerMethodField()

    class Meta:
        model = DetalleReserva
        fields = [
            'id', 'reserva', 'tipo', 'combo', 'servicio', 'promocion',
            'cantidad', 'precio_unitario', 'subtotal', 'nombre_item'
        ]
        read_only_fields = ['reserva', 'nombre_item'] # La reserva se asigna automáticamente

    def get_nombre_item(self, obj):
        if obj.combo: return obj.combo.nombre
        if obj.servicio: return obj.servicio.nombre
        if obj.promocion: return obj.promocion.nombre
        return "Ítem Desconocido"

class ReservaSerializer(serializers.ModelSerializer):
    # Permite enviar detalles anidados al crear
    detalles = DetalleReservaSerializer(many=True, required=False)
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    nombre_evento = serializers.SerializerMethodField()

    class Meta:
        model = Reserva
        fields = [
            'id', 'cliente', 'horario', 'codigo_reserva', 'fecha_evento', 
            'fecha_inicio', 'direccion_evento', 'notas_especiales', 
            'metodo_pago', 'comprobante_pago', 'transaccion_id', 'subtotal', 
            'descuento', 'impuestos', 'total', 'estado', 
            'fecha_confirmacion', 'detalles', 'cliente_nombre', 'nombre_evento'
        ]
        read_only_fields = ['cliente_nombre', 'nombre_evento']

    def get_nombre_evento(self, obj):
        # Intentar obtener el nombre del primer detalle, priorizando COMBOS
        print(f"DEBUG SERIALIZER: Evaluando reserva {obj.id}")
        queryset = obj.detalles.all()
        print(f"DEBUG SERIALIZER: Detalles encontrados: {len(queryset)}")
        
        # 1. Buscar si hay algún Combo en los detalles
        for detalle in queryset:
            print(f"DEBUG SERIALIZER: Revisando detalle {detalle.id} - Tipo {detalle.tipo} - Combo: {detalle.combo}")
            if detalle.combo:
                return detalle.combo.nombre
        
        # 2. Si no hay combo, buscar el primer Servicio o Promoción
        primer_detalle = queryset.first()
        if primer_detalle:
            if primer_detalle.servicio: return primer_detalle.servicio.nombre
            if primer_detalle.promocion: return primer_detalle.promocion.nombre
            
        print("DEBUG SERIALIZER: No se encontró nombre, retornando None")
        return None  # Retornar null si no se encuentra nada
        
    def validate_codigo_reserva(self, value):
        if not value:
            raise serializers.ValidationError("El código de reserva no puede estar vacío.")
        if Reserva.objects.filter(codigo_reserva=value).exists():
             raise serializers.ValidationError("Este código de reserva ya existe.")
        return value

    def create(self, validated_data):
        # Extraemos los detalles para guardarlos aparte
        detalles_data = validated_data.pop('detalles', [])
        print(f"DEBUG SERIALIZER CREATE: Datos de detalles recibidos: {detalles_data}")

        # Validación estricta: No crear reserva sin detalles
        if not detalles_data:
            print("DEBUG SERIALIZER CREATE: Error - Lista de detalles vacía")
            raise serializers.ValidationError({"detalles": "No se puede crear una reserva sin productos/detalles."})
        
        # Usamos una transacción para asegurar integridad de datos
        from django.db import router
        active_db = router.db_for_write(Reserva)
        
        with transaction.atomic(using=active_db):
            reserva = Reserva.objects.using(active_db).create(**validated_data)
            
            for detalle in detalles_data:
                print(f"DEBUG SERIALIZER CREATE: Creando detalle: {detalle}")
                DetalleReserva.objects.using(active_db).create(reserva=reserva, **detalle)
                
        return reserva