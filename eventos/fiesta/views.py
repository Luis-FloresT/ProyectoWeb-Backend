# 1. Standard Python Library Imports
import json
import random # Para generar códigos de reserva
import re  # Para normalizar HTML en emails
import smtplib
import traceback
import uuid
import threading # Para correos asíncronos

def run_in_background(target, *args, **kwargs):
    """
    Ejecuta una función en un hilo separado para no bloquear la respuesta.
    Ideal para envío de correos.
    """
    t = threading.Thread(target=target, args=args, kwargs=kwargs)
    t.daemon = True
    t.start()

# 2. Third-Party Library Imports (Django REST Framework)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import BasePermission, SAFE_METHODS, AllowAny, IsAuthenticated
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes, parser_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from rest_framework.authtoken.models import Token

# 3. Django Library Imports
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.shortcuts import redirect, get_object_or_404, render # get_object_or_404 importado una vez
from django.db import transaction # IMPORTANTE PARA CONFIRMAR RESERVA
from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail, EmailMessage, EmailMultiAlternatives # EmailMultiAlternatives añadido
from django.template.loader import render_to_string
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError


# 4. Local App Imports (Models and Serializers)
from .models import (
    RegistroUsuario, EmailVerificationToken,
    Promocion, Categoria, Servicio, Combo, ComboServicio,
    HorarioDisponible, Reserva, DetalleReserva, Pago, Cancelacion,
    Carrito, ItemCarrito, ConfiguracionPago, PasswordResetToken
)

from .serializers import (
    RegistroUsuarioSerializer, PromocionSerializer, CategoriaSerializer, ServicioSerializer,
    ComboDetailSerializer, ComboServicioSerializer, HorarioDisponibleSerializer, ReservaSerializer,
    DetalleReservaSerializer, PagoSerializer, CancelacionSerializer,
    CarritoSerializer, ItemCarritoSerializer, ConfiguracionPagoSerializer
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


def enviar_correo_reserva(reserva_id, detalles_previa_carga=None):
    """
    Envía dos correos de notificación: uno al cliente y otro al administrador.
    Se ejecuta en un hilo secundario para evitar bloqueos.
    """
    def _tarea_en_hilo(rid, detalles):
        try:
            # Recuperar la reserva con select_related para el cliente
            # Es necesario volver a importar/filtrar porque estamos en otro hilo,
            # pero pasamos el ID para asegurar consistencia.
            reserva = Reserva.objects.select_related('cliente').get(id=rid)

            # Usar datos en memoria si se proporcionan, de lo contrario buscar en DB
            if detalles is not None:
                detalles_procesados = detalles
            else:
                detalles_procesados = []
                # Fallback forzada si no hay datos en memoria
                for d in reserva.detalles.select_related('servicio', 'combo', 'promocion').all():
                    nombre_item = "Item no especificado"
                    if d.combo:
                        nombre_item = d.combo.nombre
                    elif d.servicio:
                        nombre_item = d.servicio.nombre
                    elif d.promocion:
                        nombre_item = d.promocion.nombre

                    detalles_procesados.append({
                        'nombre': (nombre_item or "").strip(),
                        'cantidad': d.cantidad,
                        'subtotal': d.subtotal
                    })

            # Depuración en consola
            print(f"--- DEBUG CORREO ---")
            print(f"Reserva ID: {reserva.id}")
            print(f"¿Tiene detalles?: {len(detalles_procesados) > 0}")
            for dp in detalles_procesados:
                print(f"Item Procesado: {dp['nombre']}")

            # Preparar contexto con datos limpios
            bancos = ConfiguracionPago.objects.filter(activo=True)
            dominio = "http://127.0.0.1:8000" # Cambiar por el dominio real en producción

            # Limpiar datos de reserva y cliente (usar join/split para eliminar newlines internos)
            cliente_nombre = " ".join(str(reserva.cliente.nombre or "").split())
            cliente_apellido = " ".join(str(reserva.cliente.apellido or "").split())
            codigo_reserva = (reserva.codigo_reserva or "").strip()
            direccion_evento = " ".join(str(reserva.direccion_evento or "").split())

            context = {
                'reserva': reserva,
                'cliente_nombre': cliente_nombre,
                'cliente_apellido': cliente_apellido,
                'codigo_reserva': codigo_reserva,
                'direccion_evento': direccion_evento,
                'detalles': detalles_procesados,
                'bancos': bancos,
                'dominio': dominio,
            }

            # --- 1. Correo para el CLIENTE ---
            try:
                html_cliente = render_to_string('fiesta/reserva_cliente.html', context)

                if reserva.metodo_pago == 'transferencia' or not reserva.metodo_pago:
                    asunto_cliente = f"📥 Reserva Recibida #{codigo_reserva} - Burbujitas de Colores"
                    text_cliente = f"Hola {cliente_nombre}, hemos recibido tu reserva {codigo_reserva}. Por favor realiza el pago para confirmarla."
                elif reserva.metodo_pago == 'efectivo':
                    asunto_cliente = f"💵 Reserva Recibida #{codigo_reserva} - Burbujitas de Colores"
                    text_cliente = f"Hola {cliente_nombre}, tu reserva {codigo_reserva} ha sido recibida. El pago se realizará en efectivo."
                else: # Tarjeta
                    asunto_cliente = f"🎈 Reserva Confirmada #{codigo_reserva} - Burbujitas de Colores"
                    text_cliente = f"Hola {cliente_nombre}, ¡tu reserva {codigo_reserva} ha sido confirmada!"

                msg_cliente = EmailMultiAlternatives(
                    asunto_cliente,
                    text_cliente,
                    settings.DEFAULT_FROM_EMAIL,
                    [reserva.cliente.email]
                )
                msg_cliente.attach_alternative(html_cliente, "text/html")
                msg_cliente.send(fail_silently=False)
                print(f"✅ Correo enviado al cliente: {reserva.cliente.email}")
            except Exception as e:
                print(f"❌ Error al enviar correo al cliente ({reserva.cliente.email}): {str(e)}")
                traceback.print_exc()

            # --- 2. Correo para el ADMINISTRADOR ---
            try:
                destinatario_admin = getattr(settings, 'SERVER_EMAIL', settings.DEFAULT_FROM_EMAIL)
                html_admin = render_to_string('fiesta/reserva_admin.html', context)
                
                # ULTRA-LIMPIO: Normalizar HTML para eliminar newlines
                html_admin = re.sub(r'\s+', ' ', html_admin)
                
                # ULTRA-LIMPIO: Limpiar asunto y texto plano
                asunto_admin = " ".join(f"🔔 Nueva Reserva #{codigo_reserva} - {cliente_nombre} {cliente_apellido}".split())
                text_admin = " ".join(f"Se ha recibido una nueva reserva con código {codigo_reserva} de {cliente_nombre} {cliente_apellido}.".split())

                msg_admin = EmailMultiAlternatives(
                    subject=asunto_admin,  # Sin newlines
                    body=text_admin,  # Sin newlines
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[destinatario_admin]
                )
                msg_admin.attach_alternative(html_admin, "text/html")
                msg_admin.send(fail_silently=False)
                print(f"📧 Correo enviado al administrador: {destinatario_admin}")
            except Exception as e:
                print(f"❌ Error al enviar correo al administrador ({destinatario_admin}): {str(e)}")
                traceback.print_exc()

        except Reserva.DoesNotExist:
            print(f"❌ Error: No se encontró la reserva con ID {reserva_id}")
        except Exception as e:
            print(f"❌ Error general en enviar_correo_reserva: {str(e)}")
            traceback.print_exc()

    # Lanzar hilo en background
    run_in_background(_tarea_en_hilo, reserva_id, detalles_previa_carga)


def enviar_correo_confirmacion(reserva_id):
    """
    Envía un correo festivo al cliente y un aviso profesional de logística al admin.
    Ejecución asíncrona (Thread).
    """
    def _tarea_en_hilo(rid):
        try:
            # Recuperar reserva con relaciones necesarias
            reserva = Reserva.objects.select_related('cliente').get(id=rid)
            
            # 1. Extraer detalles para el contexto (Garantizar que no esté vacío)
            detalles_items = []
            queryset_detalles = reserva.detalles.select_related('servicio', 'combo', 'promocion').all()
            
            for d in queryset_detalles:
                nombre = "Item no especificado"
                descripcion = ""
                if d.combo:
                    nombre = d.combo.nombre
                    descripcion = d.combo.descripcion
                elif d.servicio:
                    nombre = d.servicio.nombre
                    descripcion = d.servicio.descripcion
                elif d.promocion:
                    nombre = d.promocion.nombre
                    descripcion = d.promocion.descripcion

                detalles_items.append({
                    'nombre': " ".join(str(nombre or "").split()),
                    'descripcion': " ".join(str(descripcion or "").split()),
                    'cantidad': d.cantidad,
                    'precio_unitario': float(d.precio_unitario),
                    'subtotal': float(d.subtotal)
                })

            # Limpiar datos de reserva y cliente para el contexto (Join-Split para eliminar saltos internos)
            cliente_nombre = " ".join(str(reserva.cliente.nombre or "").split())
            cliente_apellido = " ".join(str(reserva.cliente.apellido or "").split())
            codigo_reserva = (reserva.codigo_reserva or "").strip()
            direccion_evento = " ".join(str(reserva.direccion_evento or "").split())
            notas_especiales = " ".join(str(reserva.notas_especiales or "").split())

            context = {
                'reserva': reserva,
                'cliente_nombre': cliente_nombre,
                'cliente_apellido': cliente_apellido,
                'codigo_reserva': codigo_reserva,
                'direccion_evento': direccion_evento,
                'notas_especiales': notas_especiales,
                'detalles': detalles_items,
                'dominio': "http://127.0.0.1:8000", # Cambiar en producción si es necesario
            }

            # --- 1. ENVÍO AL CLIENTE (HTML Festivo Mejorado) ---
            try:
                html_cliente = render_to_string('fiesta/emails/cliente_exito_confirmacion.html', context)
                asunto_cliente = f"✅ ¡Todo Listo! Evento Confirmado 🎉 - {codigo_reserva}"
                
                msg_cliente = EmailMultiAlternatives(
                    asunto_cliente,
                    f"Hola {cliente_nombre}, tu reserva #{codigo_reserva} ha sido APROBADA.",
                    settings.DEFAULT_FROM_EMAIL,
                    [reserva.cliente.email]
                )
                msg_cliente.attach_alternative(html_cliente, "text/html")
                msg_cliente.send(fail_silently=False)
                print(f"✨ Correo de CONFIRMACIÓN enviado al cliente: {reserva.cliente.email}")
            except Exception as e_cli:
                print(f"❌ Error correo cliente: {str(e_cli)}")
                traceback.print_exc()

            # --- 2. ENVÍO AL ADMINISTRADOR (HTML Logística) ---
            try:
                destinatario_admin = getattr(settings, 'SERVER_EMAIL', settings.DEFAULT_FROM_EMAIL)
                html_admin = render_to_string('fiesta/reserva_admin_logistica.html', context)
                asunto_admin = f"🚚 LOGÍSTICA: Orden de Preparación - {codigo_reserva}"
                
                msg_admin = EmailMultiAlternatives(
                    asunto_admin,
                    f"Nueva orden de logística para la reserva #{codigo_reserva}",
                    settings.DEFAULT_FROM_EMAIL,
                    [destinatario_admin]
                )
                msg_admin.attach_alternative(html_admin, "text/html")
                msg_admin.send(fail_silently=False)
                print(f"📧 Aviso de LOGÍSTICA enviado al admin: {destinatario_admin}")
            except Exception as e_adm:
                print(f"❌ Error correo admin: {str(e_adm)}")
                traceback.print_exc()
            
        except Reserva.DoesNotExist:
            print(f"❌ Error: No se encontró la reserva {reserva_id} para confirmación.")
        except Exception as e:
            print(f"❌ Error general en enviar_correo_confirmacion: {str(e)}")
            import traceback
            traceback.print_exc()
            
    # Lanzar hilo en background
    run_in_background(_tarea_en_hilo, reserva_id)


def enviar_correo_anulacion(reserva_id):
    """
    Envía un correo al cliente informando que su reserva ha sido ANULADA.
    Ejecución asíncrona.
    """
    def _tarea_en_hilo(rid):
        try:
            reserva = Reserva.objects.select_related('cliente').get(id=rid)
            cliente_nombre = (reserva.cliente.nombre or "").strip()
            codigo_reserva = (reserva.codigo_reserva or "").strip()
            
            asunto = f"❌ Reserva Anulada - #{codigo_reserva} - Burbujitas de Colores"
            mensaje = f"Hola {cliente_nombre}, te informamos que tu reserva #{codigo_reserva} ha sido anulada. Si tienes dudas, por favor contáctanos."
            
            send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [reserva.cliente.email])
            print(f"📉 Correo de ANULACIÓN enviado al cliente: {reserva.cliente.email}")
        except Exception as e:
            print(f"❌ Error al enviar correo de anulación: {str(e)}")

    run_in_background(_tarea_en_hilo, reserva_id)


# def home(request):
#     return redirect('http://localhost:5173/login')

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

            # Determinar base de datos activa para la transacción
            from django.db import router
            active_db = router.db_for_write(User)

            # --- INICIO DE TRANSACCIÓN ATÓMICA ---
            with transaction.atomic(using=active_db):
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
                # CAMBIO: URL del Frontend centralizada desde settings
                link_verificacion = f"{settings.FRONTEND_URL}/confirmar-cuenta/{token}"
                
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

    def get(self, request, token=None):
        token_value = token or request.query_params.get('token')
        if not token_value:
            return Response({'error': 'El parámetro "token" es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

        # Buscar el token
        try:
            token_obj = EmailVerificationToken.objects.get(token=token_value)
        except (EmailVerificationToken.DoesNotExist, ValidationError):
            return Response({'error': 'El enlace es inválido o ha expirado.'}, status=status.HTTP_400_BAD_REQUEST)

        # Revisar si ha expirado
        if token_obj.is_expired():
            return Response({'error': 'El token ha expirado.'}, status=status.HTTP_400_BAD_REQUEST)

        # Marcar usuario como verificado
        with transaction.atomic():
            token_obj.user.is_active = True
            token_obj.user.save()

            # Eliminar el token para que no pueda reutilizarse
            token_obj.delete()

        # Respuesta de éxito
        return Response({'message': '¡Cuenta verificada con éxito! Ya puedes iniciar sesión'}, status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    """
    Recibe un email y envía un enlace de recuperación si el usuario existe.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return Response({'message': 'El email es obligatorio'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        
        # Por seguridad, no revelamos si el usuario existe o no
        if user:
            # Eliminar tokens anteriores activos para este usuario (opcional pero recomendado)
            PasswordResetToken.objects.filter(user=user).delete()
            
            # Crear nuevo token (el UUID se genera solo)
            reset_token = PasswordResetToken.objects.create(user=user)
            
            # Preparar correo
            # Preparar correo
            # CAMBIO: URL de producción del frontend centralizada desde settings
            link_recuperacion = f"{settings.FRONTEND_URL}/restablecer-password/{user.id}/{reset_token.token}"
            
            context = {
                'user': user,
                'link_recuperacion': link_recuperacion
            }
            
            try:
                html_message = render_to_string('emails/password_reset_email.html', context)
                plain_message = f"Hola {user.username}, recupera tu contraseña aquí: {link_recuperacion}"
                
                # Extraer remitente
                import re
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
                print(f"❌ ERROR AL ENVIAR CORREO DE RECUPERACIÓN: {str(e)}")
                # No lanzamos error al usuario para persistir el mensaje genérico

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
            return Response({'message': 'Token y contraseña son obligatorios'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reset_token = PasswordResetToken.objects.get(token=token_uuid)
            
            # 1. Verificar expiración
            if reset_token.is_expired():
                reset_token.delete()
                return Response({'message': 'El enlace ha expirado. Por favor solicita uno nuevo.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 2. Actualizar contraseña de forma atómica
            from django.db import router
            active_db = router.db_for_write(User)
            with transaction.atomic(using=active_db):
                user = reset_token.user
                user.set_password(nueva_clave)
                user.save()
                
                # 3. Eliminar token tras el éxito
                reset_token.delete()
            
            return Response({'message': 'Tu contraseña ha sido actualizada correctamente.'}, status=status.HTTP_200_OK)

        except (PasswordResetToken.DoesNotExist, ValidationError):
            return Response({'message': 'El enlace es inválido o ya ha sido utilizado.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"ERROR EN RESET PASSWORD: {str(e)}")
            return Response({'message': 'Ocurrió un error al procesar tu solicitud.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

    def get_queryset(self):
        # Optimizar carga de detalles y nombres de productos
        return Reserva.objects.all().prefetch_related(
            'detalles__combo',
            'detalles__servicio',
            'detalles__promocion'
        ).order_by('-id')

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        reserva = self.get_object()
        transaccion_id = request.data.get('transaccion_id')

        if not transaccion_id:
            return Response({'error': 'El ID de transacción es obligatorio para aprobar'}, status=status.HTTP_400_BAD_REQUEST)

        # Validación Antifraude: Verificar duplicados
        duplicado = Reserva.objects.filter(transaccion_id=transaccion_id).exclude(id=reserva.id).exists()
        if duplicado:
            return Response({'error': 'ANTIFRAUDE: Este ID de transacción ya fue utilizado en otra reserva.'}, status=status.HTTP_400_BAD_REQUEST)

        reserva.transaccion_id = transaccion_id
        reserva.estado = 'APROBADA'
        reserva.fecha_confirmacion = timezone.now()
        reserva.save()

        return Response({'mensaje': 'Reserva aprobada exitosamente', 'estado': reserva.estado})

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        reserva = self.get_object()
        reserva.estado = 'ANULADA'
        reserva.save()
        return Response({'mensaje': 'Reserva anulada exitosamente', 'estado': reserva.estado})

    @action(detail=True, methods=['post'])
    def eliminar(self, request, pk=None):
        reserva = self.get_object()
        reserva.estado = 'ELIMINADA'
        reserva.save()
        return Response({'mensaje': 'Reserva marcada como eliminada', 'estado': reserva.estado})

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

                # Blindaje: Un solo evento por día/horario
                overlap = Reserva.objects.filter(
                    fecha_evento=horario.fecha,
                    horario=horario,
                    estado__in=['APROBADA', 'PENDIENTE']
                ).exists()
                
                if overlap:
                    return Response({'error': 'Este horario ya está reservado. Por favor selecciona otro día u hora.'}, status=status.HTTP_400_BAD_REQUEST)

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

            # Determinar base de datos activa para la transacción
            from django.db import router
            active_db = router.db_for_write(Reserva)

            # Crear reserva + detalle en transacción
            with transaction.atomic(using=active_db):
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
                elif promocion_id:
                    promocion_obj = Promocion.objects.get(id=promocion_id)
                    DetalleReserva.objects.create(
                        reserva=reserva,
                        tipo='P',
                        promocion=promocion_obj,
                        cantidad=1,
                        precio_unitario=promocion_obj.precio,
                        subtotal=promocion_obj.precio
                    )
                # Si hubiera promoción, se puede manejar según reglas de negocio

                # en el modelo se maneja la notificación silenciosa o por estado.
                # No enviamos correo aquí.
                pass


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
        promocion_obj = None
        precio = 0

        if tipo == 'servicio':
            servicio_obj = get_object_or_404(Servicio, pk=item_id)
            precio = servicio_obj.precio_base
        elif tipo == 'combo':
            combo_obj = get_object_or_404(Combo, pk=item_id)
            # Intentar precio_combo primero, luego precio_total si existe (fallback)
            precio = combo_obj.precio_combo or getattr(combo_obj, 'precio_total', 0)
        elif tipo == 'promocion':
            promocion_obj = get_object_or_404(Promocion, pk=item_id)
            # Priorizar precio > 0, si es 0 usar descuento_monto
            precio = promocion_obj.precio if promocion_obj.precio > 0 else (promocion_obj.descuento_monto or 0)
        
        if not servicio_obj and not combo_obj and not promocion_obj:
            return Response({'error': 'Producto no encontrado'}, status=404)

        # 5. Guardar en Carrito (Upsert)
        item, created = ItemCarrito.objects.get_or_create(
            carrito=carrito,
            servicio=servicio_obj,
            combo=combo_obj,
            promocion=promocion_obj,
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
            return Response({'error': f'No hay disponibilidad abierta para el {fecha_evento}'}, status=400)

        # Blindaje en confirmar_carrito
        overlap_carrito = Reserva.objects.filter(
            fecha_evento=fecha_evento,
            estado__in=['APROBADA', 'PENDIENTE']
        ).exists()
        
        if overlap_carrito:
            return Response({'error': 'Lo sentimos, este día ya ha sido reservado por otro usuario mientras procesabas tu pedido.'}, status=400)

        # Determinar base de datos activa para la transacción
        from django.db import router
        active_db = router.db_for_write(Reserva)

        # Transacción Atómica: O se guarda todo (reserva + detalles) o nada.
        with transaction.atomic(using=active_db):
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
            print(f"DEBUG: Moviendo {carrito.items.count()} items al detalle de reserva...")
            for item in carrito.items.all():
                try:
                    detalle = DetalleReserva.objects.create(
                        reserva=nueva_reserva,
                        tipo='S' if item.servicio else ('C' if item.combo else 'P'),
                        servicio=item.servicio,
                        combo=item.combo,
                        promocion=item.promocion,
                        cantidad=item.cantidad,
                        precio_unitario=item.precio_unitario,
                        subtotal=item.subtotal
                    )
                    print(f"DEBUG: Detalle creado ID={detalle.id} | Tipo={detalle.tipo} | Combo={detalle.combo}")
                except Exception as e:
                    print(f"DEBUG ERROR creando detalle: {e}")
                    raise e # Re-raise to trigger atomic rollback
            
            # 3. Vaciar Carrito
            carrito.items.all().delete()

            # Silencioso al inicio
            # Enviar correo de confirmación de recepción (PENDIENTE)
            try:
                # Pasamos los items en formato procesado para no depender de la DB en el template si hay delay
                detalles_memoria = []
                for item in carrito.items.all():
                    tipo_char = 'S' if item.servicio else ('C' if item.combo else 'P')
                    nombre = item.servicio.nombre if item.servicio else (item.combo.nombre if item.combo else item.promocion.nombre)
                    detalles_memoria.append({'nombre': nombre, 'cantidad': item.cantidad, 'subtotal': item.subtotal})
                
                enviar_correo_reserva(nueva_reserva.id, detalles_previa_carga=detalles_memoria)
            except Exception as e:
                print(f"⚠️ Error enviando correo inicial: {e}")


        return Response({
            'mensaje': 'Reserva creada con éxito', 
            'codigo': nueva_reserva.codigo_reserva
        }, status=201)

    except Exception as e:
        print(f"ERROR CONFIRMACION: {str(e)}")
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def checkout_pago(request, reserva_id):
    """
    Endpoint para que el usuario elija el método de pago y suba el comprobante si es transferencia.
    """
    print(f"--- DEBUG CHECKOUT PAGO ---")
    print(f"Reserva ID: {reserva_id}")
    print(f"Content-Type: {request.content_type}")
    print(f"Data: {request.data}")
    print(f"Files: {request.FILES}")

    reserva = get_object_or_404(Reserva, id=reserva_id, cliente__email=request.user.email)
    
    metodo = request.data.get('metodo_pago')
    if metodo not in ['transferencia', 'tarjeta', 'efectivo']:
        print(f"Metodo no valido: {metodo}")
        return Response({'error': 'Método de pago no válido'}, status=400)
    
    reserva.metodo_pago = metodo
    
    if metodo == 'transferencia':
        comprobante = request.FILES.get('comprobante_pago')
        if comprobante:
            print(f"Comprobante recibido: {comprobante.name}")
            reserva.comprobante_pago = comprobante
        else:
            print("No se recibio comprobante")
            # El estado sigue siendo PENDIENTE hasta que el administrador valide
    elif metodo == 'tarjeta':
        # En una integración real, aquí recibiríamos el token o ID de la pasarela
        transaccion_id = request.data.get('transaccion_id')
        if transaccion_id:
            reserva.transaccion_id = transaccion_id
            # Si hay transaccion_id, asumimos éxito parcial o confirmación
            # reserva.estado = 'APROBADA' # Opcional automatizarlo
    elif metodo == 'efectivo':
        # Pago en efectivo: suele ser al momento del evento o en oficina
        reserva.comprobante_pago = None
        reserva.transaccion_id = None
        
    reserva.save()
    
    # Notificar por correo del cambio de método (opcional, pero útil)
    # Por ahora, si es tarjeta y tenemos ID, podríamos enviar el correo de confirmación
    response_data = {
        'mensaje': f'Método de pago {metodo} configurado correctamente',
        'metodo_pago': reserva.metodo_pago,
        'estado': reserva.estado
    }

    if metodo == 'transferencia':
        bancos = ConfiguracionPago.objects.filter(activo=True)
        response_data['bancos'] = ConfiguracionPagoSerializer(bancos, many=True).data

    if metodo == 'tarjeta' and reserva.transaccion_id:
        # Aquí se podría automatizar el cambio a APROBADA
        # reserva.estado = 'APROBADA'
        # reserva.save()
        pass
    elif metodo == 'efectivo':
        pass
    
    if metodo == 'transferencia' and comprobante:
        # Notificar al administrador que hay un nuevo comprobante
        enviar_notificacion_comprobante(reserva.id)

    return Response(response_data, status=200)

def enviar_notificacion_comprobante(reserva_id):
    """
    Notifica al admin cuando se sube una foto de pago.
    ULTRA-LIMPIO: Elimina TODOS los saltos de línea antes de enviar a Brevo.
    """
    try:
        from django.conf import settings
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from .models import Reserva
        import re
        
        reserva = Reserva.objects.get(id=reserva_id)
        destinatario_admin = getattr(settings, 'SERVER_EMAIL', settings.DEFAULT_FROM_EMAIL)
        
        # 🔍 DEBUG: Verificar qué datos tiene la reserva realmente
        print(f"--- DEBUG RESERVA: {reserva.id} ---")
        print(f"Total Crudo: {reserva.total}")
        print(f"Cliente Crudo: {reserva.cliente}")
        print(f"Código: {reserva.codigo_reserva}")
        
        # ========================================================================
        # PASO 1: Limpiar TODAS las variables para evitar newlines en Brevo
        # ========================================================================
        
        # Intentar obtener el nombre del cliente (con fallback al User de Django si está vacío)
        raw_nombre = reserva.cliente.nombre or ""
        raw_apellido = reserva.cliente.apellido or ""
        
        # Si el nombre viene del señal automático o está vacío, intentar buscar en el User
        if (not raw_nombre or raw_nombre == reserva.cliente.email) and hasattr(reserva.cliente, 'email'):
            from django.contrib.auth.models import User
            user_obj = User.objects.filter(email=reserva.cliente.email).first()
            if user_obj:
                raw_nombre = user_obj.first_name or user_obj.username
                raw_apellido = user_obj.last_name
        
        nombre_completo = " ".join(f"{raw_nombre} {raw_apellido}".strip().split())
        cliente_telefono = " ".join(str(reserva.cliente.telefono or "").split())
        codigo_reserva = " ".join(str(reserva.codigo_reserva or "").split())
        direccion_evento = " ".join(str(reserva.direccion_evento or "").split())
        notas_especiales = " ".join(str(reserva.notas_especiales or "").split())
        metodo_pago = " ".join(str(reserva.metodo_pago or "").split())
        
        # Formatear total con 2 decimales y limpiar
        # Forzamos 0.00 si es None o 0 para evitar cadenas vacías
        monto_total = reserva.total if reserva.total is not None else 0
        total_formateado = " ".join(f"{float(monto_total):.2f}".split())
        
        print(f"DEBUG PROCESADO -> Nombre: '{nombre_completo}' | Total: '{total_formateado}'")
        
        # Contexto para el template con TODOS los posibles nombres de variables
        # para que coincida con cualquier versión de la plantilla en Brevo
        context = {
            'reserva': reserva,
            'cliente_nombre_completo': nombre_completo, 
            'nombre_completo': nombre_completo,        
            'cliente_nombre': nombre_completo,         
            'cliente_telefono': cliente_telefono,
            'codigo_reserva': codigo_reserva,
            'direccion_evento': direccion_evento,
            'notas_especiales': notas_especiales,
            'metodo_pago': metodo_pago,
            'total': total_formateado,
            'dominio': "http://127.0.0.1:8000",
            'params': { 
                 'cliente_nombre_completo': nombre_completo,
                 'total': total_formateado,
                 'codigo_reserva': codigo_reserva
            }
        }

        # ========================================================================
        # PASO 2: Generar contenido HTML y limpiarlo (Nueva Plantilla Profesional)
        # ========================================================================
        html_content = render_to_string('fiesta/emails/notificacion_admin.html', context)
        # ULTRA-LIMPIO: Normalizar HTML para eliminar saltos de línea que rompen Brevo
        html_content = re.sub(r'\s+', ' ', html_content).strip()
        
        # ========================================================================
        # PASO 3: Limpiar asunto y texto plano (CRÍTICO para Brevo)
        # ========================================================================
        asunto = " ".join(f"📸 NUEVO PAGO SUBIDO - Reserva #{codigo_reserva}".split())
        text_content = " ".join(f"Nuevo pago subido para reserva #{codigo_reserva}. Monto: ${total_formateado}".split())
        
        # ========================================================================
        # PASO 4: Enviar email con TODAS las cadenas limpias
        # ========================================================================
        msg = EmailMultiAlternatives(
            subject=asunto,  # Sin newlines
            body=text_content,  # Sin newlines
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario_admin]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        print(f"✅ Notificación de comprobante enviada al admin para reserva {codigo_reserva}")
    except Exception as e:
        print(f"❌ Error notificando comprobante: {e}")
        import traceback
        traceback.print_exc()


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


class ConfiguracionPagoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint para obtener los datos bancarios configurados.
    """
    queryset = ConfiguracionPago.objects.filter(activo=True)
    serializer_class = ConfiguracionPagoSerializer
    permission_classes = [AllowAny] # Cualquier usuario puede ver los datos para pagar

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
