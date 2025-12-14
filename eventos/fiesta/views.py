from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import BasePermission, SAFE_METHODS, AllowAny
from rest_framework.decorators import action
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import HttpResponse
from rest_framework.authtoken.models import Token
from django.db.models import Q
import uuid
from .models import ItemCarrito

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


from rest_framework_simplejwt.tokens import RefreshToken

class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        usuario = request.data.get('usuario')
        clave = request.data.get('clave')

        user = authenticate(username=usuario, password=clave)
        if not user:
            return Response(
                {'message': 'Credenciales inválidas'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            'id': user.id,
            'username': user.username,
            'is_admin': user.is_staff,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class RegistroUsuarioView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

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

# ------ PERMISOS PERSONALIZADOS ------
class SoloLecturaOAdmin(BasePermission):
    """Permite lectura pública, pero solo admin puede crear/editar/eliminar"""
    def has_permission(self, request, view):
        return (
            request.method in SAFE_METHODS or
            (request.user and request.user.is_staff)
        )

class SoloUsuariosAutenticados(BasePermission):
    """Requiere autenticación para cualquier acción"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
# ---------------------------------------

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
    permission_classes = [SoloLecturaOAdmin]  # Público para GET, admin para modificar

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
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def disponibles(self, request):
        """
        Obtiene horarios disponibles para una fecha específica.
        Query params: ?fecha=YYYY-MM-DD
        Devuelve solo horarios que no tienen reservas confirmadas.
        """
        fecha = request.query_params.get('fecha')
        
        if not fecha:
            return Response(
                {'error': 'Parámetro "fecha" es obligatorio (formato: YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Obtener horarios para esa fecha
            horarios = HorarioDisponible.objects.filter(fecha=fecha, disponible=True)
            
            # Filtrar solo horarios sin reservas confirmadas
            horarios_libres = []
            for horario in horarios:
                # Contar reservas confirmadas en ese horario
                reservas_confirmadas = Reserva.objects.filter(
                    horario=horario,
                    estado__in=['CONFIRMADA', 'PENDIENTE']
                ).count()
                
                # Si el horario tiene capacidad, lo incluimos
                if reservas_confirmadas < horario.capacidad_reserva:
                    horarios_libres.append(horario)
            
            serializer = HorarioDisponibleSerializer(horarios_libres, many=True)
            return Response(serializer.data)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            ) 

class ReservaViewSet(viewsets.ModelViewSet):
    queryset = Reserva.objects.all()
    serializer_class = ReservaSerializer
    permission_classes = [SoloUsuariosAutenticados]  # Solo usuarios autenticados
    
    def create(self, request, *args, **kwargs):
        """
        Crea una reserva validando que el horario esté disponible.
        """
        try:
            horario_id = request.data.get('horario')
            
            # Validar que el horario existe
            try:
                horario = HorarioDisponible.objects.get(id=horario_id)
            except HorarioDisponible.DoesNotExist:
                return Response(
                    {'error': 'El horario seleccionado no existe'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar que el horario está disponible
            if not horario.disponible:
                return Response(
                    {'error': 'Este horario no está disponible'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Contar reservas en ese horario
            reservas_actuales = Reserva.objects.filter(
                horario=horario,
                estado__in=['CONFIRMADA', 'PENDIENTE']
            ).count()
            
            if reservas_actuales >= horario.capacidad_reserva:
                return Response(
                    {'error': 'Este horario ya no tiene disponibilidad'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Buscar o crear el RegistroUsuario asociado al usuario autenticado
            registro = RegistroUsuario.objects.filter(email=request.user.email).first()
            if not registro:
                email = request.user.email or f"{request.user.username}@example.com"
                telefono = f"000-{uuid.uuid4().hex[:8]}"  # valor único de respaldo
                registro = RegistroUsuario.objects.create(
                    nombre=request.user.username or "usuario",
                    apellido="",
                    telefono=telefono,
                    email=email,
                    contrasena="autogenerada"
                )

            # Preparar datos completos para el serializer
            data = request.data.copy()
            data['cliente'] = registro.id  # Enlazar con RegistroUsuario

            # Campos monetarios requeridos en el modelo
            total = data.get('total') or 0
            data.setdefault('subtotal', total)
            data.setdefault('descuento', 0)
            data.setdefault('impuestos', 0)

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DetalleReservaViewSet(viewsets.ModelViewSet):
    queryset = DetalleReserva.objects.all()
    serializer_class = DetalleReservaSerializer

class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
    permission_classes = [SoloUsuariosAutenticados]  # Solo usuarios autenticados

class CancelacionViewSet(viewsets.ModelViewSet):
    queryset = Cancelacion.objects.all()
    serializer_class = CancelacionSerializer
    permission_classes = [SoloUsuariosAutenticados]  # Solo usuarios autenticados
