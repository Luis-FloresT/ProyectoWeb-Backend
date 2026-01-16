# fiesta/auth_views.py
import uuid
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import RegistroUsuario, EmailVerificationToken
from .serializers import RegistroUsuarioSerializer

class RegistroUsuarioView(APIView):
    """Registro de usuario con token de verificación de email."""
    def post(self, request):
        data = request.data
        email = data.get("email")
        password = data.get("contrasena")
        nombre = data.get("nombre")
        apellido = data.get("apellido")
        telefono = data.get("telefono")

        if User.objects.filter(email=email).exists():
            return Response({"error": "Este correo ya está registrado."}, status=status.HTTP_400_BAD_REQUEST)

        # Crear usuario Django
        user = User.objects.create_user(username=email, email=email, password=password, first_name=nombre, last_name=apellido)
        user.is_active = False  # Se activa después de verificar el email
        user.save()

        # Crear perfil adicional
        perfil = RegistroUsuario.objects.create(user=user, nombre=nombre, apellido=apellido, telefono=telefono)

        # Crear token de verificación
        token = str(uuid.uuid4())
        EmailVerificationToken.objects.create(user=user, token=token)

        # Enviar email
        verification_link = f"http://localhost:5173/verificar-email/?token={token}"
        send_mail(
            'Verifica tu correo',
            f'Hola {nombre},\n\nPor favor verifica tu correo usando el siguiente enlace:\n{verification_link}\n\nGracias!',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

        serializer = RegistroUsuarioSerializer(perfil)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class VerificarEmailView(APIView):
    """Verificación del token de correo."""
    def get(self, request):
        token = request.GET.get("token")
        if not token:
            return Response({"error": "Token no proporcionado."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token_obj = EmailVerificationToken.objects.get(token=token)
        except EmailVerificationToken.DoesNotExist:
            return Response({"error": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)

        if token_obj.is_expired():
            return Response({"error": "Token expirado."}, status=status.HTTP_400_BAD_REQUEST)

        user = token_obj.user
        user.is_active = True
        user.save()

        token_obj.delete()  # eliminar token tras verificación
        return Response({"success": "Correo verificado correctamente."}, status=status.HTTP_200_OK)


class LoginView(APIView):
    """Login de usuarios (solo si están verificados)."""
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("contrasena")

        user = authenticate(username=email, password=password)
        if user is None:
            return Response({"error": "Credenciales inválidas."}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({"error": "El correo no ha sido verificado."}, status=status.HTTP_403_FORBIDDEN)

        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "success": "Inicio de sesión exitoso.",
            "user_id": user.id,
            "email": user.email,
            "token": token.key
        }, status=status.HTTP_200_OK)
