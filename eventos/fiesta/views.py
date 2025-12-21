# 1. Standard Python Library Imports
import json
import random # Para generar códigos de reserva
import smtplib
import traceback
import uuid

# 2. Third-Party Library Imports (Django REST Framework)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import BasePermission, SAFE_METHODS, AllowAny, IsAuthenticated
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication



from rest_framework.authtoken.models import Token

# 3. Django Library Imports
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.shortcuts import redirect, get_object_or_404, render # get_object_or_404 importado una vez
from django.db import transaction # IMPORTANTE PARA CONFIRMAR RESERVA
from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail, EmailMessage # EmailMessage importado una vez
from django.template.loader import render_to_string
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError


# 4. Local App Imports (Models and Serializers)






# 4. Local App Imports (Models and Serializers)
from .models import (
    RegistroUsuario, EmailVerificationToken,
    Promocion, Categoria, Servicio, Combo, ComboServicio,
    HorarioDisponible, Reserva, DetalleReserva, Pago, Cancelacion,
    Carrito, ItemCarrito 
)

from .serializers import (
    RegistroUsuarioSerializer, PromocionSerializer, CategoriaSerializer, ServicioSerializer,
    ComboDetailSerializer, ComboServicioSerializer, HorarioDisponibleSerializer, ReservaSerializer,
    DetalleReservaSerializer, PagoSerializer, CancelacionSerializer,
    CarritoSerializer, ItemCarritoSerializer
)




def enviar_correo(asunto, mensaje, destinatario, proveedor='gmail'):
    """
    Envía correo usando la configuración de Django. Intenta usar el backend
    de Django (`EmailMessage.send()`), y si hay error hace un fallback a smtplib
    usando la configuración del proveedor.
    """
    if proveedor == 'gmail':
        config = settings.EMAIL_GMAIL
    elif proveedor == 'outlook':
        config = settings.EMAIL_OUTLOOK
    elif proveedor == 'brevo':
        config = None
    else:
        raise ValueError("Proveedor no soportado")

    # Determinar remitente de forma segura: primero DEFAULT_FROM_EMAIL, luego USERNAME del config si existe
    default_from = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
    if not default_from:
        default_from = config.get('USERNAME') if config else None

    email = EmailMessage(
        subject=asunto,
        body=mensaje,
        from_email=default_from,
        to=[destinatario],
    )
    email.content_subtype = "plain"

    try:
        # Si se solicita Brevo, preferimos API si está configurada, sino usamos SMTP relay
        if proveedor == 'brevo':
            api_key = getattr(settings, 'BREVO_API_KEY', '')
            if api_key:
                import requests
                import re
                
                # Extraer solo el email del formato "Nombre <email@example.com>"
                from_email_raw = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
                email_match = re.search(r'<(.+?)>', from_email_raw)
                sender_email = email_match.group(1) if email_match else from_email_raw
                
                # Extraer el nombre si existe
                name_match = re.match(r'^(.+?)\s*<', from_email_raw)
                sender_name = name_match.group(1).strip() if name_match else "Burbujitas de Colores"
                
                payload = {
                    "sender": {"name": sender_name, "email": sender_email},
                    "to": [{"email": destinatario}],
                    "subject": asunto,
                    "textContent": mensaje,
                }
                headers = {
                    'api-key': api_key,
                    'Content-Type': 'application/json'
                }
                resp = requests.post('https://api.sendinblue.com/v3/smtp/email', json=payload, headers=headers, timeout=10)
                print(f"BREVO RESPONSE: {resp.status_code} {resp.text}") # DEBUG LOG
                if resp.status_code >= 400:
                    raise RuntimeError(f'Brevo API error: {resp.status_code} {resp.text}')
                return
            # si no hay API key, usar SMTP relay configurado en settings.EMAIL_BREVO
            brevo_cfg = getattr(settings, 'EMAIL_BREVO', {})
            if not brevo_cfg or not brevo_cfg.get('USERNAME'):
                raise RuntimeError('Brevo no configurado: neither BREVO_API_KEY nor EMAIL_BREVO SMTP credentials are set')
            # enviar por SMTP relay
            import smtplib
            with smtplib.SMTP(brevo_cfg['HOST'], brevo_cfg['PORT']) as server:
                if brevo_cfg.get('USE_TLS'):
                    server.starttls()
                server.login(brevo_cfg['USERNAME'], brevo_cfg['PASSWORD'])
                server.sendmail(brevo_cfg['USERNAME'], [destinatario], email.message().as_string())
            return

        # Usar el backend configurado en settings (recomendado)
        email.send(fail_silently=False)
    except Exception as e:
        # Si el proveedor es Brevo no intentamos fallback SMTP con una config inexistente;
        # re-levantar para que el llamante vea el error y lo loguee.
        if proveedor == 'brevo':
            raise
        # Fallback directo con smtplib si el backend falla
        try:
            import smtplib
            with smtplib.SMTP(config['HOST'], config['PORT']) as server:
                if config.get('USE_TLS'):
                    server.starttls()
                server.login(config['USERNAME'], config['PASSWORD'])
                server.sendmail(config['USERNAME'], [destinatario], email.message().as_string())
        except Exception:
            # Re-levantar para que el código llamante lo vea y lo pueda loguear
            raise





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
        
        # 1. Verificar si el usuario existe
        try:
            user_obj = User.objects.get(username=usuario)
        except User.DoesNotExist:
            return Response({'message': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

        # 2. Verificar contraseña
        if not user_obj.check_password(clave):
            return Response({'message': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)
            
        # 3. Verificar que el correo ha sido verificado
        if not user_obj.is_active:
            return Response({'message': 'Debes verificar tu correo electrónico antes de poder iniciar sesión.'}, status=status.HTTP_403_FORBIDDEN)
            
        # 4. Login exitoso
        token, created = Token.objects.get_or_create(user=user_obj)
        cliente = RegistroUsuario.objects.filter(email=user_obj.email).first()
        cliente_id = cliente.id if cliente else None

        return Response({
            'id': user_obj.id,
            'cliente_id': cliente_id,
            'username': user_obj.username,
            'is_admin': user_obj.is_staff,
            'token': token.key
        }, status=status.HTTP_200_OK)





class RegistroUsuarioView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            nombre = request.data.get('nombre', '').strip()
            email = request.data.get('email', '').strip()
            clave = request.data.get('clave', '').strip()
            apellido = request.data.get('apellido', '').strip()
            telefono = request.data.get('telefono', '').strip()

            # 1️⃣, 2️⃣, 3️⃣ Validaciones de campos obligatorios e email
            if not nombre or not email or not clave:
                return Response(
                    {'message': 'Campos obligatorios faltantes.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                validate_email(email)
            except ValidationError:
                return Response({'message': 'Email inválido.'}, status=status.HTTP_400_BAD_REQUEST)

            # 4️⃣ Validar contraseña
            if len(clave) < 6:
                return Response({'message': 'La contraseña debe tener al menos 6 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)

            # 5️⃣ Verificar si usuario, email o teléfono ya existen
            if User.objects.filter(username=nombre).exists():
                return Response({'message': 'Ese usuario ya existe.'}, status=status.HTTP_400_BAD_REQUEST)
            if User.objects.filter(email=email).exists():
                return Response({'message': 'Ese correo ya está registrado.'}, status=status.HTTP_400_BAD_REQUEST)
            if RegistroUsuario.objects.filter(telefono=telefono).exists():
                return Response({'message': 'Ese teléfono ya está registrado.'}, status=status.HTTP_400_BAD_REQUEST)

            # --- INICIO DE TRANSACCIÓN ATÓMICA ---
            with transaction.atomic():
                # 6️⃣ Crear usuario INACTIVO (debe verificar correo para loguearse)
                user = User.objects.create_user(username=nombre, email=email, password=clave)
                user.is_active = False  # Solo puede loguearse DESPUÉS de verificar email
                user.save()

                # =========================================================================
                # 7️⃣ Obtener o actualizar RegistroUsuario (creado automáticamente por signal)
                # =========================================================================
                try:
                    # Intentar obtener el RegistroUsuario creado por el signal automático (buscar por email)
                    registro = RegistroUsuario.objects.get(email=email)
                    
                    # Actualizar los campos que el signal podría no haber llenado
                    registro.nombre = nombre
                    registro.apellido = apellido if apellido else ''
                    registro.telefono = telefono if telefono else ''
                    registro.save()
                
                except RegistroUsuario.DoesNotExist:
                    # Si no se creó automáticamente (no hay signal), crear manualmente
                    registro = RegistroUsuario.objects.create(
                        nombre=nombre,
                        apellido=apellido if apellido else '',
                        email=email,
                        telefono=telefono if telefono else '',
                        contrasena='managed_by_django'  # La contraseña se maneja en User
                    )

                # 7️⃣ Sincronizar con RegistroUsuario (Perfil)
                # (Nota) No usamos FK a User en RegistroUsuario; sincronizamos por email.

                # 8️⃣ Crear token de verificación
                token = str(uuid.uuid4())
                EmailVerificationToken.objects.create(user=user, token=token)

                # 9️⃣ Preparar correo de verificación
                link_verificacion = f"http://127.0.0.1:8000/api/verificar-email/?token={token}"
                context = {
                    'nombre': nombre,
                    'link_verificacion': link_verificacion
                }
                html_message = render_to_string('emails/verification_email.html', context)
                plain_message = f"Hola {nombre}, verifica tu correo aquí: {link_verificacion}"

                # Extraer solo el email del DEFAULT_FROM_EMAIL
                import re
                from_email_raw = settings.DEFAULT_FROM_EMAIL
                email_match = re.search(r'<(.+?)>', from_email_raw)
                sender_email = email_match.group(1) if email_match else from_email_raw

                try:
                    send_mail(
                        subject='🎈 Verifica tu correo - Burbujitas de Colores',
                        message=plain_message,
                        from_email=sender_email,
                        recipient_list=[email],
                        html_message=html_message,
                        fail_silently=False
                    )
                    print(f"✅ CORREO HTML ENVIADO A: {email}")
                except Exception as e:
                    # Loggeamos el error pero no revertimos la creación del usuario si el correo falla
                    # OJO: Si queremos que el registro falle si el correo no se envía, 
                    # deberíamos mover este bloque fuera o lanzar una excepción aquí.
                    # Por ahora lo dejamos como un log para no frustrar al usuario si el servidor de correo falla.
                    print(f"❌ ERROR AL ENVIAR CORREO: {str(e)}")

            # --- FIN DE TRANSACCIÓN ATÓMICA ---

            return Response({'message': 'Usuario registrado correctamente. Revisa tu correo para verificar tu cuenta.'}, status=status.HTTP_201_CREATED)

        except IntegrityError as e:
            print("ERROR DE INTEGRIDAD EN REGISTRO:")
            traceback.print_exc()
            return Response({'message': 'Error de integridad en los datos. Posible duplicado.', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print("ERROR INESPERADO EN REGISTRO:")
            traceback.print_exc()
            return Response({'message': 'Error inesperado durante el registro.', 'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SendTestEmailView(APIView):
    """Enviar un correo de prueba usando el backend configurado (SendGrid/SMTP/Console)."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        to_email = request.data.get('email') or request.query_params.get('email')
        if not to_email:
            return Response({'error': 'El campo "email" es requerido (body JSON o query param).'}, status=status.HTTP_400_BAD_REQUEST)

        subject = request.data.get('subject', 'Correo de prueba Django')
        body = request.data.get('body', 'Este es un correo de prueba enviado desde la API de prueba.')

        try:
            # Usar el backend configurado en settings (SMTP Brevo)
            email = EmailMessage(
                subject=subject, 
                body=body, 
                to=[to_email], 
                from_email=settings.DEFAULT_FROM_EMAIL
            )
            email.content_subtype = 'plain'
            email.send(fail_silently=False)
            
            return Response({'message': 'Correo enviado via SMTP.'}, status=status.HTTP_200_OK)
        except Exception as e:
            traceback.print_exc()
            return Response({'error': 'Fallo al enviar correo', 'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerificarEmailView(APIView):
    """
    Verifica el correo de un usuario usando un token enviado por email.
    URL: /verificar-email/?token=<token>
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        token_value = request.query_params.get('token')
        if not token_value:
            return Response({'error': 'El parámetro "token" es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

        # Buscar el token
        token_obj = get_object_or_404(EmailVerificationToken, token=token_value)

        # Revisar si ha expirado
        if token_obj.is_expired():
            return Response({'error': 'El token ha expirado.'}, status=status.HTTP_400_BAD_REQUEST)

        # Marcar usuario como verificado
        token_obj.user.is_active = True
        token_obj.user.save()

        # Eliminar el token para que no pueda reutilizarse
        token_obj.delete()

        # Renderizar página de éxito
        return render(request, 'emails/verification_success.html')




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

    def create(self, request, *args, **kwargs):
        """
        Crear reserva requiriendo un horario disponible definido por el admin.
        - Valida cliente autenticado
        - Valida horario (existencia, disponible y capacidad)
        - Ajusta fecha_evento según el horario
        - Calcula subtotal e impuestos si falta
        - Crea DetalleReserva para servicio/combo
        """
        try:
            data = request.data.copy()

            # Cliente desde el usuario autenticado
            cliente = RegistroUsuario.objects.filter(email=request.user.email).first()
            if not cliente:
                return Response({'error': 'No se encontró tu perfil de cliente'}, status=status.HTTP_404_NOT_FOUND)

            # Código de reserva si no existe
            if not data.get('codigo_reserva'):
                data['codigo_reserva'] = f"RES-{random.randint(1000,9999)}-{uuid.uuid4().hex[:4].upper()}"

            # Horario requerido
            horario_id = data.get('horario')
            if not horario_id:
                return Response({'error': 'Debes seleccionar un horario disponible'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                horario = HorarioDisponible.objects.get(id=horario_id, disponible=True)
            except HorarioDisponible.DoesNotExist:
                return Response({'error': 'El horario seleccionado no está disponible'}, status=status.HTTP_400_BAD_REQUEST)

            # Capacidad del horario
            reservas_en_horario = Reserva.objects.filter(
                horario=horario,
                estado__in=['CONFIRMADA', 'PENDIENTE']
            ).count()
            if reservas_en_horario >= horario.capacidad_reserva:
                return Response({'error': 'Este horario ya está lleno. Por favor selecciona otro'}, status=status.HTTP_400_BAD_REQUEST)

            # Alinear fecha_evento y hora_inicio con horario
            data['fecha_evento'] = horario.fecha
            data['fecha_inicio'] = horario.hora_inicio

            # Totales
            total = float(data.get('total', 0))
            if total > 0 and not data.get('subtotal'):
                subtotal = total / 1.12
                impuestos = total - subtotal
                data['subtotal'] = round(subtotal, 2)
                data['impuestos'] = round(impuestos, 2)
            elif not data.get('subtotal'):
                data['subtotal'] = 0
                data['impuestos'] = 0

            # Extraer posibles ítems
            servicio_id = data.pop('servicio', None)
            combo_id = data.pop('combo', None)
            promocion_id = data.pop('promocion', None)

            # Cliente correcto en la reserva
            data['cliente'] = cliente.id

            # Crear reserva + detalle en transacción
            with transaction.atomic():
                serializer = self.get_serializer(data=data)
                if not serializer.is_valid():
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                reserva = serializer.save()

                # Detalle
                if servicio_id:
                    servicio = Servicio.objects.get(id=servicio_id)
                    DetalleReserva.objects.create(
                        reserva=reserva,
                        tipo='S',
                        servicio=servicio,
                        cantidad=1,
                        precio_unitario=servicio.precio_base,
                        subtotal=servicio.precio_base
                    )
                elif combo_id:
                    combo = Combo.objects.get(id=combo_id)
                    DetalleReserva.objects.create(
                        reserva=reserva,
                        tipo='C',
                        combo=combo,
                        cantidad=1,
                        precio_unitario=combo.precio_combo,
                        subtotal=combo.precio_combo
                    )
                # Si hubiera promoción, se puede manejar según reglas de negocio

            headers = self.get_success_headers(serializer.data)
            return Response(
                {
                    'mensaje': 'Reserva creada exitosamente',
                    'codigo_reserva': reserva.codigo_reserva,
                    'reserva': serializer.data
                },
                status=status.HTTP_201_CREATED,
                headers=headers
            )

        except Exception as e:
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
