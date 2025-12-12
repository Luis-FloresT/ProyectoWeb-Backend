from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import HttpResponse
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from .models import (
    RegistroUsuario, Promocion, Categoria, Servicio, Combo, ComboServicio,
    HorarioDisponible, Reserva, DetalleReserva, Pago, Cancelacion
)
from .serializers import (
    RegistroUsuarioSerializer, PromocionSerializer, CategoriaSerializer, ServicioSerializer,
    ComboDetailSerializer, ComboServicioSerializer, HorarioDisponibleSerializer, ReservaSerializer,
    DetalleReservaSerializer, PagoSerializer, CancelacionSerializer
)

def home(request):
    return HttpResponse("Bienvenido al sistema de eventos y fiestas 🎉")


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    def post(self, request):
        usuario = request.data.get('usuario')
        clave = request.data.get('clave')
        user = authenticate(username=usuario, password=clave)
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'id': user.id,
                'username': user.username,
                'is_admin': user.is_staff,
                'token': token.key
            })
        return Response({'message': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

class RegistroUsuarioView(APIView):
    def post(self, request):
        nombre = request.data.get('nombre')
        email = request.data.get('email')
        clave = request.data.get('clave')
        if not nombre or not email or not clave:
            return Response({'message': 'Campos obligatorios faltantes.'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=nombre).exists():
            return Response({'message': 'Ese usuario ya existe'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(username=nombre, email=email, password=clave)
        return Response({'message': 'Usuario registrado correctamente'})

class RegistroUsuarioViewSet(viewsets.ModelViewSet):
    queryset = RegistroUsuario.objects.all()
    serializer_class = RegistroUsuarioSerializer

# ------ PERMISO SOLO LECTURA O ADMIN ------
class SoloLecturaOAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.method in SAFE_METHODS or
            (request.user and request.user.is_staff)
        )
# ------------------------------------------

class PromocionViewSet(viewsets.ModelViewSet):
    queryset = Promocion.objects.all()
    serializer_class = PromocionSerializer
    permission_classes = [SoloLecturaOAdmin]  # <--- SOLO admin puede modificar, todos pueden ver

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [SoloLecturaOAdmin]

class ServicioViewSet(viewsets.ModelViewSet):
    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer

class ComboViewSet(viewsets.ModelViewSet):
    queryset = Combo.objects.all()
    serializer_class = ComboDetailSerializer
    permission_classes = [SoloLecturaOAdmin]

class ComboServicioViewSet(viewsets.ModelViewSet):
    queryset = ComboServicio.objects.all()
    serializer_class = ComboServicioSerializer

class HorarioDisponibleViewSet(viewsets.ModelViewSet):
    queryset = HorarioDisponible.objects.all()
    serializer_class = HorarioDisponibleSerializer
    permission_classes = [SoloLecturaOAdmin] 

class ReservaViewSet(viewsets.ModelViewSet):
    queryset = Reserva.objects.all()
    serializer_class = ReservaSerializer

class DetalleReservaViewSet(viewsets.ModelViewSet):
    queryset = DetalleReserva.objects.all()
    serializer_class = DetalleReservaSerializer

class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer

class CancelacionViewSet(viewsets.ModelViewSet):
    queryset = Cancelacion.objects.all()
    serializer_class = CancelacionSerializer
