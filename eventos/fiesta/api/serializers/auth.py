from rest_framework import serializers
from fiesta.models import RegistroUsuario


class RegistroUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroUsuario
        fields = ['id', 'nombre', 'apellido', 'email', 'telefono']
