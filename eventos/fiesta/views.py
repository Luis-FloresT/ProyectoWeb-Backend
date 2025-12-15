from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import BasePermission, SAFE_METHODS, AllowAny, IsAuthenticated
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.shortcuts import redirect, get_object_or_404
from django.db import transaction # <--- IMPORTANTE PARA CONFIRMAR RESERVA
import uuid
import json 
import random # <--- PARA GENERAR CODIGOS DE RESERVA

# IMPORTAMOS MODELOS Y SERIALIZERS
from .models import (
    RegistroUsuario, Promocion, Categoria, Servicio, Combo, ComboServicio,
    HorarioDisponible, Reserva, DetalleReserva, Pago, Cancelacion,
    Carrito, ItemCarrito 
)

from .serializers import (
    RegistroUsuarioSerializer, PromocionSerializer, CategoriaSerializer, ServicioSerializer,
    ComboDetailSerializer, ComboServicioSerializer, HorarioDisponibleSerializer, ReservaSerializer,
    DetalleReservaSerializer, PagoSerializer, CancelacionSerializer,
    CarritoSerializer, ItemCarritoSerializer
)

# ==========================================
# 0. VISTA INICIAL
# ==========================================
def home(request):
    return redirect('http://localhost:5173/login')

# ==========================================
# 1. AUTENTICACIÓN
# ==========================================
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        usuario = request.data.get('usuario')
        clave = request.data.get('clave')
        user = authenticate(username=usuario, password=clave)
        
        if user:
            token, created = Token.objects.get_or_create(user=user)
            cliente = RegistroUsuario.objects.filter(email=user.email).first()
            cliente_id = cliente.id if cliente else None

            return Response({
                'id': user.id,
                'cliente_id': cliente_id,
                'username': user.username,
                'is_admin': user.is_staff,
                'token': token.key
            })
        return Response({'message': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

class RegistroUsuarioView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        nombre = request.data.get('nombre')
        email = request.data.get('email')
        clave = request.data.get('clave')
        
        if not nombre or not email or not clave:
            return Response({'message': 'Campos faltantes.'}, status=400)
        
        if User.objects.filter(username=nombre).exists():
            return Response({'message': 'Usuario ya existe'}, status=400)
        
        User.objects.create_user(username=nombre, email=email, password=clave)
        
        RegistroUsuario.objects.create(
            nombre=nombre, 
            apellido="", 
            email=email, 
            telefono=f"000-{uuid.uuid4().hex[:6]}", 
            contrasena=clave
        )
        return Response({'message': 'Usuario registrado correctamente'})

class RegistroUsuarioViewSet(viewsets.ModelViewSet):
    queryset = RegistroUsuario.objects.all()
    serializer_class = RegistroUsuarioSerializer

# ==========================================
# 2. PERMISOS Y CATÁLOGO
# ==========================================
class SoloLecturaOAdmin(BasePermission):
    def has_permission(self, request, view):
        return (request.method in SAFE_METHODS or (request.user and request.user.is_staff))

class SoloUsuariosAutenticados(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [SoloLecturaOAdmin]

class PromocionViewSet(viewsets.ModelViewSet):
    queryset = Promocion.objects.all()
    serializer_class = PromocionSerializer
    permission_classes = [SoloLecturaOAdmin]

class ServicioViewSet(viewsets.ModelViewSet):
    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer
    permission_classes = [SoloLecturaOAdmin]

class ComboViewSet(viewsets.ModelViewSet):
    queryset = Combo.objects.all()
    serializer_class = ComboDetailSerializer
    permission_classes = [SoloLecturaOAdmin]

class ComboServicioViewSet(viewsets.ModelViewSet):
    queryset = ComboServicio.objects.all()
    serializer_class = ComboServicioSerializer

# ==========================================
# 3. GESTIÓN DE RESERVAS
# ==========================================
class HorarioDisponibleViewSet(viewsets.ModelViewSet):
    queryset = HorarioDisponible.objects.all()
    serializer_class = HorarioDisponibleSerializer
    permission_classes = [SoloLecturaOAdmin]
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def disponibles(self, request):
        fecha = request.query_params.get('fecha')
        if not fecha: return Response({'error': 'Falta fecha'}, status=400)
        
        horarios = HorarioDisponible.objects.filter(fecha=fecha, disponible=True)
        libres = []
        for h in horarios:
            confirmadas = Reserva.objects.filter(horario=h, estado__in=['CONFIRMADA', 'PENDIENTE']).count()
            if confirmadas < h.capacidad_reserva:
                libres.append(h)
        return Response(HorarioDisponibleSerializer(libres, many=True).data)

class ReservaViewSet(viewsets.ModelViewSet):
    queryset = Reserva.objects.all()
    serializer_class = ReservaSerializer
    permission_classes = [SoloUsuariosAutenticados]

class DetalleReservaViewSet(viewsets.ModelViewSet):
    queryset = DetalleReserva.objects.all()
    serializer_class = DetalleReservaSerializer

class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
    permission_classes = [SoloUsuariosAutenticados]

class CancelacionViewSet(viewsets.ModelViewSet):
    queryset = Cancelacion.objects.all()
    serializer_class = CancelacionSerializer
    permission_classes = [SoloUsuariosAutenticados]

# ==========================================
# 4. GESTIÓN DEL CARRITO COMPLETA
# ==========================================

# A. Vista para agregar items
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def agregar_al_carrito(request):
    print("--- INTENTO DE AGREGAR AL CARRITO ---")
    
    try:
        # 1. Obtener datos estandarizados
        tipo = request.data.get('tipo') 
        item_id = request.data.get('item_id')
        cantidad = int(request.data.get('cantidad', 1))

        if not tipo or not item_id:
            return Response({'error': 'Faltan datos: tipo o item_id requeridos'}, status=400)

        # 2. Identificar Cliente
        cliente = RegistroUsuario.objects.filter(email=request.user.email).first()
        if not cliente:
            return Response({'error': 'No se encontró tu perfil de cliente.'}, status=404)

        # 3. Buscar/Crear Carrito
        carrito, _ = Carrito.objects.get_or_create(cliente=cliente)

        # 4. Identificar Producto y Precio
        servicio_obj = None
        combo_obj = None
        precio = 0

        if tipo == 'servicio':
            servicio_obj = get_object_or_404(Servicio, pk=item_id)
            precio = servicio_obj.precio_base
        elif tipo == 'combo':
            combo_obj = get_object_or_404(Combo, pk=item_id)
            precio = combo_obj.precio_combo
        
        if not servicio_obj and not combo_obj:
            return Response({'error': 'Producto no encontrado'}, status=404)

        # 5. Guardar en Carrito (Upsert)
        item, created = ItemCarrito.objects.get_or_create(
            carrito=carrito,
            servicio=servicio_obj,
            combo=combo_obj,
            defaults={'precio_unitario': precio, 'cantidad': 0}
        )
        
        item.cantidad += cantidad
        item.precio_unitario = precio 
        item.save()

        return Response({
            'mensaje': 'Producto agregado correctamente', 
            'item': ItemCarritoSerializer(item).data
        }, status=200)

    except Exception as e:
        print(f"ERROR CARRITO: {str(e)}")
        return Response({'error': str(e)}, status=500)

# B. Vista para confirmar y convertir en Reserva
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def confirmar_carrito(request):
    print("--- CONFIRMANDO RESERVA ---")
    try:
        # Datos del formulario
        fecha_evento = request.data.get('fecha_evento')
        direccion = request.data.get('direccion_evento')
        
        if not fecha_evento or not direccion:
            return Response({'error': 'Fecha y dirección son obligatorias'}, status=400)

        cliente = RegistroUsuario.objects.filter(email=request.user.email).first()
        carrito = Carrito.objects.filter(cliente=cliente).first()

        if not carrito or not carrito.items.exists():
            return Response({'error': 'El carrito está vacío'}, status=400)

        # Calcular Totales
        subtotal_total = sum(item.subtotal for item in carrito.items.all())
        impuestos = float(subtotal_total) * 0.12 # Ejemplo 12%
        total = float(subtotal_total) + impuestos

        # Asignar un horario disponible (Lógica simplificada: toma el primero del día)
        # Nota: Idealmente el usuario debería elegir el bloque horario específico
        horario = HorarioDisponible.objects.filter(fecha=fecha_evento).first()
        
        if not horario:
            # Si no hay horarios creados para ese día, no se puede reservar
            return Response({'error': f'No hay disponibilidad abierta para el {fecha_evento}'}, status=400)

        # Transacción Atómica: O se guarda todo (reserva + detalles) o nada.
        with transaction.atomic():
            # 1. Crear Reserva
            nueva_reserva = Reserva.objects.create(
                cliente=cliente,
                horario=horario,
                codigo_reserva=f"RES-{random.randint(1000,9999)}-{uuid.uuid4().hex[:4].upper()}",
                fecha_evento=fecha_evento,
                fecha_inicio=horario.hora_inicio,
                direccion_evento=direccion,
                subtotal=subtotal_total,
                impuestos=impuestos,
                total=total,
                estado='PENDIENTE'
            )

            # 2. Mover items de Carrito a DetalleReserva
            for item in carrito.items.all():
                DetalleReserva.objects.create(
                    reserva=nueva_reserva,
                    tipo='S' if item.servicio else 'C',
                    servicio=item.servicio,
                    combo=item.combo,
                    cantidad=item.cantidad,
                    precio_unitario=item.precio_unitario,
                    subtotal=item.subtotal
                )
            
            # 3. Vaciar Carrito
            carrito.items.all().delete()

        return Response({
            'mensaje': 'Reserva creada con éxito', 
            'codigo': nueva_reserva.codigo_reserva
        }, status=201)

    except Exception as e:
        print(f"ERROR CONFIRMACION: {str(e)}")
        return Response({'error': str(e)}, status=500)

# C. ViewSet para gestionar el carrito (Ver)
class CarritoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Carrito.objects.all()
    serializer_class = CarritoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Carrito.objects.filter(cliente__email=user.email)
        return Carrito.objects.none()

# D. ViewSet para gestionar items individuales (Eliminar)
class ItemCarritoViewSet(viewsets.ModelViewSet):
    queryset = ItemCarrito.objects.all()
    serializer_class = ItemCarritoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Solo permite gestionar items de TU propio carrito
        if self.request.user.is_authenticated:
            return ItemCarrito.objects.filter(carrito__cliente__email=self.request.user.email)
        return ItemCarrito.objects.none()