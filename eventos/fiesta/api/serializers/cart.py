from rest_framework import serializers
from fiesta.models import Carrito, ItemCarrito


class ItemCarritoSerializer(serializers.ModelSerializer):
    nombre_producto = serializers.SerializerMethodField()
    
    def get_nombre_producto(self, obj):
        if obj.servicio:
            return obj.servicio.nombre
        elif obj.combo:
            return obj.combo.nombre
        elif obj.promocion:
            return obj.promocion.nombre
        return "Producto desconocido"
    
    class Meta:
        model = ItemCarrito
        fields = ['id', 'nombre_producto', 'servicio', 'combo', 'promocion', 'cantidad', 'precio_unitario', 'subtotal']


class CarritoSerializer(serializers.ModelSerializer):
    items = ItemCarritoSerializer(many=True, read_only=True)

    class Meta:
        model = Carrito
        fields = ['id', 'cliente', 'items', 'creado_en', 'actualizado_en']
