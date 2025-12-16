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
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import EmailVerificationToken
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.shortcuts import render, get_object_or_404
import uuid
from django.conf import settings
from django.core.mail import EmailMessage
import smtplib
import traceback
import uuid
from .models import RegistroUsuario, EmailVerificationToken
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError



from .models import (
    RegistroUsuario, Promocion, Categoria, Servicio, Combo, ComboServicio,
    HorarioDisponible, Reserva, DetalleReserva, Pago, Cancelacion
)
from .serializers import (
    RegistroUsuarioSerializer, PromocionSerializer, CategoriaSerializer, ServicioSerializer,
    ComboDetailSerializer, ComboServicioSerializer, HorarioDisponibleSerializer, ReservaSerializer,
    DetalleReservaSerializer, PagoSerializer, CancelacionSerializer
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
                payload = {
                    "sender": {"name": "No-Reply", "email": getattr(settings, 'DEFAULT_FROM_EMAIL', None)},
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
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # 1️⃣ Obtener datos y limpiar espacios
            nombre = request.data.get('nombre', '').strip()
            email = request.data.get('email', '').strip()
            clave = request.data.get('clave', '').strip()
            apellido = request.data.get('apellido', '').strip()
            telefono = request.data.get('telefono', '').strip()

            # 2️⃣ Validar campos obligatorios
            if not nombre or not email or not clave:
                return Response(
                    {'message': 'Campos obligatorios faltantes.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 3️⃣ Validar email
            try:
                validate_email(email)
            except ValidationError:
                return Response({'message': 'Email inválido.'}, status=status.HTTP_400_BAD_REQUEST)

            # 4️⃣ Validar contraseña
            if len(clave) < 6:
                return Response({'message': 'La contraseña debe tener al menos 6 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)

            # 5️⃣ Verificar si usuario o email existen
            if User.objects.filter(username=nombre).exists():
                return Response({'message': 'Ese usuario ya existe.'}, status=status.HTTP_400_BAD_REQUEST)
            if User.objects.filter(email=email).exists():
                return Response({'message': 'Ese correo ya está registrado.'}, status=status.HTTP_400_BAD_REQUEST)

            # 6️⃣ Crear usuario inactivo
            user = User.objects.create_user(username=nombre, email=email, password=clave)
            user.is_active = False
            user.save()

            # 7️⃣ Crear registro asociado
            registro = RegistroUsuario.objects.create(
                user=user,
                nombre=nombre,
                apellido=apellido,
                telefono=telefono
            )

            # 8️⃣ Crear token de verificación
            token = str(uuid.uuid4())
            EmailVerificationToken.objects.create(user=user, token=token)

            # 9️⃣ Enviar correo de verificación
            link_verificacion = f"http://127.0.0.1:8000/api/verificar-email/?token={token}"
            try:
                # Elegir proveedor: si BREVO_API_KEY está configurada usamos Brevo,
                # si no, dejamos que el backend de Django (AnyMail/SendGrid o SMTP)
                # procese el envío usando EmailMessage.send().
                # Renderizar template HTML
                html_message = render_to_string('fiesta/email_verificacion.html', {
                    'nombre': nombre,
                    'link_verificacion': link_verificacion
                })
                
                # Usa el backend configurado (SMTP Brevo)
                email_msg = EmailMessage(
                    subject='🎈 Verifica tu correo - Burbujitas de Colores',
                    body=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email]
                )
                email_msg.content_subtype = 'html' # Enviar como HTML
                email_msg.send(fail_silently=False)
            except Exception:
                print("ERROR AL ENVIAR CORREO:")
                traceback.print_exc()

            # 1️⃣0️⃣ Respuesta exitosa
            return Response({'message': 'Usuario registrado correctamente. Revisa tu correo para verificar tu cuenta.'})

        except IntegrityError as e:
            print("ERROR DE BASE DE DATOS:")
            traceback.print_exc()
            return Response({'message': 'Error en base de datos', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print("ERROR INESPERADO EN REGISTRO USUARIO:")
            traceback.print_exc()
            return Response({'message': 'Error inesperado', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


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

        # Marcar usuario como activo/verificado (opcional)
        token_obj.user.is_active = True
        token_obj.user.save()

        # Opcional: eliminar el token para que no pueda reutilizarse
        token_obj.delete()

        # Renderizar página de éxito
        return render(request, 'fiesta/verificacion_exito.html')


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

# `enviar_correo` está unificada al inicio del archivo y usa el backend de Django.