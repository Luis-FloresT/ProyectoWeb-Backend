import traceback
import re
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

from fiesta.models import (
    RegistroUsuario, HorarioDisponible, Reserva, DetalleReserva,
    ConfiguracionPago, Pago, Cancelacion
)
from fiesta.api.serializers.bookings import (
    HorarioDisponibleSerializer, ReservaSerializer, DetalleReservaSerializer,
    PagoSerializer, CancelacionSerializer, ConfiguracionPagoSerializer
)
from fiesta.api.permissions import SoloLecturaOAdmin, SoloUsuariosAutenticados
from fiesta.api.utils import run_in_background, limpiar_texto, generar_codigo_reserva


def enviar_correo_reserva(reserva_id, detalles_previa_carga=None):
    """
    Envía correos de notificación: uno al cliente y otro al administrador.
    Se ejecuta en hilo secundario para evitar bloqueos.
    """
    def _tarea_en_hilo(rid, detalles):
        try:
            reserva = Reserva.objects.select_related('cliente').get(id=rid)

            if detalles is not None:
                detalles_procesados = detalles
            else:
                detalles_procesados = []
                for d in reserva.detalles.select_related('servicio', 'combo', 'promocion').all():
                    nombre_item = "Item no especificado"
                    if d.combo:
                        nombre_item = d.combo.nombre
                    elif d.servicio:
                        nombre_item = d.servicio.nombre
                    elif d.promocion:
                        nombre_item = d.promocion.nombre

                    detalles_procesados.append({
                        'nombre': limpiar_texto(nombre_item),
                        'cantidad': d.cantidad,
                        'subtotal': d.subtotal
                    })

            bancos = ConfiguracionPago.objects.filter(activo=True)
            dominio = "http://127.0.0.1:8000"

            cliente_nombre = limpiar_texto(reserva.cliente.nombre or "")
            cliente_apellido = limpiar_texto(reserva.cliente.apellido or "")
            codigo_reserva = limpiar_texto(reserva.codigo_reserva or "")
            direccion_evento = limpiar_texto(reserva.direccion_evento or "")

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

            # Correo para el CLIENTE
            try:
                html_cliente = render_to_string('fiesta/reserva_cliente.html', context)

                if reserva.metodo_pago == 'transferencia' or not reserva.metodo_pago:
                    asunto_cliente = f"📥 Reserva Recibida #{codigo_reserva} - Burbujitas de Colores"
                    text_cliente = f"Hola {cliente_nombre}, hemos recibido tu reserva {codigo_reserva}. Por favor realiza el pago para confirmarla."
                elif reserva.metodo_pago == 'efectivo':
                    asunto_cliente = f"💵 Reserva Recibida #{codigo_reserva} - Burbujitas de Colores"
                    text_cliente = f"Hola {cliente_nombre}, tu reserva {codigo_reserva} ha sido recibida. El pago se realizará en efectivo."
                else:
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
                print(f"❌ Error correo cliente: {str(e)}")
                traceback.print_exc()

            # Correo para el ADMINISTRADOR
            try:
                destinatario_admin = getattr(settings, 'SERVER_EMAIL', settings.DEFAULT_FROM_EMAIL)
                html_admin = render_to_string('fiesta/reserva_admin.html', context)
                html_admin = re.sub(r'\s+', ' ', html_admin)
                
                asunto_admin = limpiar_texto(f"🔔 Nueva Reserva #{codigo_reserva} - {cliente_nombre} {cliente_apellido}")
                text_admin = limpiar_texto(f"Se ha recibido una nueva reserva con código {codigo_reserva} de {cliente_nombre} {cliente_apellido}.")

                msg_admin = EmailMultiAlternatives(
                    subject=asunto_admin,
                    body=text_admin,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[destinatario_admin]
                )
                msg_admin.attach_alternative(html_admin, "text/html")
                msg_admin.send(fail_silently=False)
                print(f"📧 Correo enviado al administrador: {destinatario_admin}")
            except Exception as e:
                print(f"❌ Error correo admin: {str(e)}")
                traceback.print_exc()

        except Reserva.DoesNotExist:
            print(f"❌ Reserva no encontrada: {rid}")
        except Exception as e:
            print(f"❌ Error general: {str(e)}")
            traceback.print_exc()

    run_in_background(_tarea_en_hilo, reserva_id, detalles_previa_carga)


def enviar_correo_confirmacion(reserva_id):
    """
    Envía correos festivos al cliente y profesionales de logística al admin.
    """
    def _tarea_en_hilo(rid):
        try:
            reserva = Reserva.objects.select_related('cliente').get(id=rid)
            
            detalles_items = []
            for d in reserva.detalles.select_related('servicio', 'combo', 'promocion').all():
                nombre = "Item no especificado"
                if d.combo:
                    nombre = d.combo.nombre
                elif d.servicio:
                    nombre = d.servicio.nombre
                elif d.promocion:
                    nombre = d.promocion.nombre

                detalles_items.append({
                    'nombre': limpiar_texto(nombre),
                    'cantidad': d.cantidad,
                    'precio_unitario': float(d.precio_unitario),
                    'subtotal': float(d.subtotal)
                })

            cliente_nombre = limpiar_texto(reserva.cliente.nombre or "")
            cliente_apellido = limpiar_texto(reserva.cliente.apellido or "")
            codigo_reserva = limpiar_texto(reserva.codigo_reserva or "")
            direccion_evento = limpiar_texto(reserva.direccion_evento or "")
            notas_especiales = limpiar_texto(reserva.notas_especiales or "")

            context = {
                'reserva': reserva,
                'cliente_nombre': cliente_nombre,
                'cliente_apellido': cliente_apellido,
                'codigo_reserva': codigo_reserva,
                'direccion_evento': direccion_evento,
                'notas_especiales': notas_especiales,
                'detalles': detalles_items,
                'dominio': "http://127.0.0.1:8000",
            }

            # Correo al CLIENTE
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
                print(f"✨ Correo de confirmación enviado al cliente: {reserva.cliente.email}")
            except Exception as e:
                print(f"❌ Error correo cliente: {str(e)}")
                traceback.print_exc()

            # Correo al ADMINISTRADOR
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
                print(f"📧 Aviso de logística enviado al admin: {destinatario_admin}")
            except Exception as e:
                print(f"❌ Error correo admin: {str(e)}")
                traceback.print_exc()
            
        except Reserva.DoesNotExist:
            print(f"❌ Reserva no encontrada: {rid}")
        except Exception as e:
            print(f"❌ Error general: {str(e)}")
            traceback.print_exc()
            
    run_in_background(_tarea_en_hilo, reserva_id)


def enviar_correo_anulacion(reserva_id):
    """
    Envía correos de notificación cuando una reserva es anulada.
    """
    def _tarea_en_hilo(rid):
        try:
            reserva = Reserva.objects.select_related('cliente').get(id=rid)
            
            cliente_nombre = limpiar_texto(reserva.cliente.nombre or "")
            cliente_apellido = limpiar_texto(reserva.cliente.apellido or "")
            codigo_reserva = limpiar_texto(reserva.codigo_reserva or "")

            context = {
                'reserva': reserva,
                'cliente_nombre': cliente_nombre,
                'cliente_apellido': cliente_apellido,
                'codigo_reserva': codigo_reserva,
            }

            # Correo al CLIENTE
            try:
                asunto_cliente = f"❌ Reserva Anulada - {codigo_reserva}"
                text_cliente = f"Hola {cliente_nombre}, lamentamos informarte que tu reserva #{codigo_reserva} ha sido anulada."
                
                msg_cliente = EmailMultiAlternatives(
                    asunto_cliente,
                    text_cliente,
                    settings.DEFAULT_FROM_EMAIL,
                    [reserva.cliente.email]
                )
                msg_cliente.send(fail_silently=False)
                print(f"📧 Correo de anulación enviado al cliente: {reserva.cliente.email}")
            except Exception as e:
                print(f"❌ Error correo cliente anulación: {str(e)}")
                traceback.print_exc()
            
        except Reserva.DoesNotExist:
            print(f"❌ Reserva no encontrada: {rid}")
        except Exception as e:
            print(f"❌ Error general: {str(e)}")
            traceback.print_exc()
            
    run_in_background(_tarea_en_hilo, reserva_id)


class HorarioDisponibleViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar horarios disponibles.
    Solo lectura para usuarios normales, CRUD para admins.
    Incluye acción personalizada para obtener horarios disponibles por fecha.
    """
    queryset = HorarioDisponible.objects.all()
    serializer_class = HorarioDisponibleSerializer
    permission_classes = [SoloLecturaOAdmin]
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def disponibles(self, request):
        """
        Obtiene horarios disponibles para una fecha específica.
        Query param: ?fecha=YYYY-MM-DD
        """
        fecha = request.query_params.get('fecha')
        if not fecha:
            return Response({'error': 'Falta fecha'}, status=400)
        
        horarios = HorarioDisponible.objects.filter(fecha=fecha, disponible=True)
        libres = []
        for h in horarios:
            confirmadas = Reserva.objects.filter(
                horario=h, 
                estado__in=['CONFIRMADA', 'PENDIENTE']
            ).count()
            if confirmadas < h.capacidad_reserva:
                libres.append(h)
        return Response(HorarioDisponibleSerializer(libres, many=True).data)


class ReservaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar reservas.
    Solo usuarios autenticados pueden crear y ver reservas.
    """
    queryset = Reserva.objects.all()
    serializer_class = ReservaSerializer
    permission_classes = [SoloUsuariosAutenticados]

    def get_queryset(self):
        return Reserva.objects.all().prefetch_related(
            'detalles__combo',
            'detalles__servicio',
            'detalles__promocion'
        )

    def create(self, request, *args, **kwargs):
        """
        Crear reserva con validación de horario disponible.
        """
        try:
            data = request.data.copy()

            cliente = RegistroUsuario.objects.filter(email=request.user.email).first()
            if not cliente:
                return Response({
                    'error': 'No se encontró tu perfil de cliente'
                }, status=status.HTTP_404_NOT_FOUND)

            if not data.get('codigo_reserva'):
                data['codigo_reserva'] = generar_codigo_reserva()

            horario_id = data.get('horario')
            if not horario_id:
                return Response({
                    'error': 'Debes seleccionar un horario disponible'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                horario = HorarioDisponible.objects.get(id=horario_id, disponible=True)
            except HorarioDisponible.DoesNotExist:
                return Response({
                    'error': 'El horario seleccionado no está disponible'
                }, status=status.HTTP_400_BAD_REQUEST)

            data['fecha_evento'] = horario.fecha
            data['fecha_inicio'] = horario.hora_inicio

            total = float(data.get('total', 0))
            if total > 0 and not data.get('subtotal'):
                subtotal = total / 1.12
                impuestos = total - subtotal
                data['subtotal'] = round(subtotal, 2)
                data['impuestos'] = round(impuestos, 2)
            elif not data.get('subtotal'):
                data['subtotal'] = 0
                data['impuestos'] = 0

            servicio_id = data.pop('servicio', None)
            combo_id = data.pop('combo', None)
            promocion_id = data.pop('promocion', None)

            data['cliente'] = cliente.id

            with transaction.atomic():
                serializer = self.get_serializer(data=data)
                if not serializer.is_valid():
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                reserva = serializer.save()

                if servicio_id:
                    from fiesta.models import Servicio
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
                    from fiesta.models import Combo
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
                    from fiesta.models import Promocion
                    promocion = Promocion.objects.get(id=promocion_id)
                    DetalleReserva.objects.create(
                        reserva=reserva,
                        tipo='P',
                        promocion=promocion,
                        cantidad=1,
                        precio_unitario=promocion.precio,
                        subtotal=promocion.precio
                    )

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
    """
    ViewSet para gestionar detalles de reservas.
    """
    queryset = DetalleReserva.objects.all()
    serializer_class = DetalleReservaSerializer


class PagoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar pagos.
    Solo usuarios autenticados.
    """
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
    permission_classes = [SoloUsuariosAutenticados]


class CancelacionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar cancelaciones de reservas.
    Solo usuarios autenticados.
    """
    queryset = Cancelacion.objects.all()
    serializer_class = CancelacionSerializer
    permission_classes = [SoloUsuariosAutenticados]


class ConfiguracionPagoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint para obtener datos bancarios configurados.
    Cualquier usuario puede ver esta información para realizar pagos.
    """
    queryset = ConfiguracionPago.objects.filter(activo=True)
    serializer_class = ConfiguracionPagoSerializer
    permission_classes = [AllowAny]
