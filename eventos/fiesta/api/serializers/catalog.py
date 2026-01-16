from rest_framework import serializers
from fiesta.models import Categoria, Promocion, Servicio, Combo, ComboServicio


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'


class PromocionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promocion
        fields = '__all__'


class ServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        fields = '__all__'


class ComboServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComboServicio
        fields = '__all__'


class ComboDetailSerializer(serializers.ModelSerializer):
    servicios = ComboServicioSerializer(source='combos_servicio', many=True, read_only=True)

    class Meta:
        model = Combo
        fields = '__all__'
