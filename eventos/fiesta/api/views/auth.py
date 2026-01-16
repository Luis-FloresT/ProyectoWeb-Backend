import uuid
import traceback
import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404, render
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from rest_framework.authtoken.models import Token

from fiesta.models import RegistroUsuario, EmailVerificationToken, PasswordResetToken


class LoginView(APIView):
    """
    Endpoint para login de usuarios.
    Requiere usuario y contraseña.
    Retorna token de autenticación si es exitoso.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        usuario = request.data.get('usuario')
        clave = request.data.get('clave')
        
        # Verificar si el usuario existe
        try:
            user_obj = User.objects.get(username=usuario)
        except User.DoesNotExist:
            return Response({'message': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

        # Verificar contraseña
        if not user_obj.check_password(clave):
            return Response({'message': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)
            
        # Verificar que el correo ha sido verificado
        if not user_obj.is_active:
            return Response({
                'message': 'Debes verificar tu correo electrónico antes de poder iniciar sesión.'
            }, status=status.HTTP_403_FORBIDDEN)
            
        # Login exitoso
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
    """
    Endpoint para registro de nuevos usuarios.
    Crea usuario inactivo y envía email de verificación.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            nombre = request.data.get('nombre', '').strip()
            email = request.data.get('email', '').strip()
            clave = request.data.get('clave', '').strip()
            apellido = request.data.get('apellido', '').strip()
            telefono = request.data.get('telefono', '').strip()

            # Validaciones de campos obligatorios
            if not nombre or not email or not clave:
                return Response(
                    {'message': 'Campos obligatorios faltantes.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar email
            try:
                validate_email(email)
            except ValidationError:
                return Response({'message': 'Email inválido.'}, status=status.HTTP_400_BAD_REQUEST)

            # Validar contraseña
            if len(clave) < 6:
                return Response({
                    'message': 'La contraseña debe tener al menos 6 caracteres.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Verificar si usuario, email o teléfono ya existen
            if User.objects.filter(username=nombre).exists():
                return Response({'message': 'Ese usuario ya existe.'}, status=status.HTTP_400_BAD_REQUEST)
            if User.objects.filter(email=email).exists():
                return Response({'message': 'Ese correo ya está registrado.'}, status=status.HTTP_400_BAD_REQUEST)
            if RegistroUsuario.objects.filter(telefono=telefono).exists():
                return Response({'message': 'Ese teléfono ya está registrado.'}, status=status.HTTP_400_BAD_REQUEST)

            # Transacción atómica
            with transaction.atomic():
                # Crear usuario inactivo (debe verificar correo para loguearse)
                user = User.objects.create_user(username=nombre, email=email, password=clave)
                user.is_active = False
                user.save()

                # Obtener o crear RegistroUsuario
                try:
                    registro = RegistroUsuario.objects.get(email=email)
                    registro.nombre = nombre
                    registro.apellido = apellido if apellido else ''
                    registro.telefono = telefono if telefono else ''
                    registro.save()
                except RegistroUsuario.DoesNotExist:
                    registro = RegistroUsuario.objects.create(
                        nombre=nombre,
                        apellido=apellido if apellido else '',
                        email=email,
                        telefono=telefono if telefono else '',
                        contrasena='managed_by_django'
                    )

                # Crear token de verificación
                token = str(uuid.uuid4())
                EmailVerificationToken.objects.create(user=user, token=token)

                # Preparar correo de verificación
                domain = "http://localhost:8000"
                link_verificacion = f"{domain}/api/verificar-email/?token={token}"
                
                context = {
                    'nombre': nombre,
                    'link_verificacion': link_verificacion
                }
                html_message = render_to_string('emails/verification_email.html', context)
                plain_message = f"Hola {nombre}, verifica tu correo aquí: {link_verificacion}"

                # Extraer remitente
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
                    print(f"✅ CORREO ENVIADO A: {email}")
                except Exception as e:
                    print(f"❌ ERROR AL ENVIAR CORREO: {str(e)}")

            return Response({
                'message': 'Usuario registrado correctamente. Revisa tu correo para verificar tu cuenta.'
            }, status=status.HTTP_201_CREATED)

        except IntegrityError as e:
            print("ERROR DE INTEGRIDAD EN REGISTRO:")
            traceback.print_exc()
            return Response({
                'message': 'Error de integridad en los datos. Posible duplicado.',
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print("ERROR INESPERADO EN REGISTRO:")
            traceback.print_exc()
            return Response({
                'message': 'Error inesperado durante el registro.',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SendTestEmailView(APIView):
    """Enviar un correo de prueba usando el backend configurado."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        to_email = request.data.get('email') or request.query_params.get('email')
        if not to_email:
            return Response({
                'error': 'El campo "email" es requerido (body JSON o query param).'
            }, status=status.HTTP_400_BAD_REQUEST)

        subject = request.data.get('subject', 'Correo de prueba Django')
        body = request.data.get('body', 'Este es un correo de prueba enviado desde la API de prueba.')

        try:
            from django.core.mail import EmailMessage
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
            return Response({
                'error': 'Fallo al enviar correo',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            return Response({
                'error': 'El parámetro "token" es obligatorio.'
            }, status=status.HTTP_400_BAD_REQUEST)

        token_obj = get_object_or_404(EmailVerificationToken, token=token_value)

        # Revisar si ha expirado
        if token_obj.is_expired():
            return Response({'error': 'El token ha expirado.'}, status=status.HTTP_400_BAD_REQUEST)

        # Marcar usuario como verificado
        token_obj.user.is_active = True
        token_obj.user.save()

        # Eliminar el token
        token_obj.delete()

        # Renderizar página de éxito
        return render(request, 'emails/verification_success.html')


class PasswordResetRequestView(APIView):
    """
    Recibe un email y envía un enlace de recuperación si el usuario existe.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return Response({
                'message': 'El email es obligatorio'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        
        # Por seguridad, no revelamos si el usuario existe
        if user:
            # Eliminar tokens anteriores para este usuario
            PasswordResetToken.objects.filter(user=user).delete()
            
            # Crear nuevo token
            reset_token = PasswordResetToken.objects.create(user=user)
            
            # Preparar correo
            frontend_domain = "http://localhost:5173"
            link_recuperacion = f"{frontend_domain}/reset-password/{reset_token.token}"
            
            context = {
                'user': user,
                'link_recuperacion': link_recuperacion
            }
            
            try:
                html_message = render_to_string('emails/password_reset_email.html', context)
                plain_message = f"Hola {user.username}, recupera tu contraseña aquí: {link_recuperacion}"
                
                # Extraer remitente
                from_email_raw = settings.DEFAULT_FROM_EMAIL
                email_match = re.search(r'<(.+?)>', from_email_raw)
                sender_email = email_match.group(1) if email_match else from_email_raw

                send_mail(
                    subject='🔑 Recuperación de Contraseña - Burbujitas de Colores',
                    message=plain_message,
                    from_email=sender_email,
                    recipient_list=[email],
                    html_message=html_message,
                    fail_silently=False
                )
                print(f"✅ CORREO DE RECUPERACIÓN ENVIADO A: {email}")
            except Exception as e:
                print(f"❌ ERROR AL ENVIAR CORREO: {str(e)}")

        return Response({
            'message': 'Si el correo está registrado, recibirás un enlace para restablecer tu contraseña en breve.'
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """
    Valida el token y actualiza la contraseña del usuario.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        token_uuid = request.data.get('token')
        nueva_clave = request.data.get('password')

        if not token_uuid or not nueva_clave:
            return Response({
                'message': 'Token y contraseña son obligatorios'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            reset_token = PasswordResetToken.objects.get(token=token_uuid)
            
            # Verificar expiración
            if reset_token.is_expired():
                reset_token.delete()
                return Response({
                    'message': 'El enlace ha expirado. Por favor solicita uno nuevo.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Actualizar contraseña de forma atómica
            with transaction.atomic():
                user = reset_token.user
                user.set_password(nueva_clave)
                user.save()
                
                # Eliminar token tras el éxito
                reset_token.delete()
            
            return Response({
                'message': 'Tu contraseña ha sido actualizada correctamente.'
            }, status=status.HTTP_200_OK)

        except (PasswordResetToken.DoesNotExist, ValidationError):
            return Response({
                'message': 'El enlace es inválido o ya ha sido utilizado.'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"ERROR EN RESET PASSWORD: {str(e)}")
            return Response({
                'message': 'Ocurrió un error al procesar tu solicitud.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
