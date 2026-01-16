from rest_framework import viewsets

from fiesta.models import (
    RegistroUsuario, Categoria, Promocion, Servicio, Combo, ComboServicio
)
from fiesta.api.serializers.auth import RegistroUsuarioSerializer
from fiesta.api.serializers.catalog import (
    CategoriaSerializer, PromocionSerializer,
    ServicioSerializer, ComboDetailSerializer, ComboServicioSerializer
)
from fiesta.api.permissions import SoloLecturaOAdmin


class RegistroUsuarioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar usuarios registrados.
    Operaciones CRUD completas con permisos de solo lectura o admin.
    """
    queryset = RegistroUsuario.objects.all()
    serializer_class = RegistroUsuarioSerializer
    permission_classes = [SoloLecturaOAdmin]


class CategoriaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar categorías de productos.
    Solo lectura para usuarios normales, CRUD para admins.
    """
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [SoloLecturaOAdmin]


class PromocionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar promociones.
    Solo lectura para usuarios normales, CRUD para admins.
    """
    queryset = Promocion.objects.all()
    serializer_class = PromocionSerializer
    permission_classes = [SoloLecturaOAdmin]


class ServicioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar servicios disponibles.
    Solo lectura para usuarios normales, CRUD para admins.
    """
    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer
    permission_classes = [SoloLecturaOAdmin]


class ComboViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar combos de servicios.
    Solo lectura para usuarios normales, CRUD para admins.
    """
    queryset = Combo.objects.all()
    serializer_class = ComboDetailSerializer
    permission_classes = [SoloLecturaOAdmin]


class ComboServicioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar la relación entre combos y servicios.
    """
    queryset = ComboServicio.objects.all()
    serializer_class = ComboServicioSerializer
