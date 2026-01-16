import traceback
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, status
from django.shortcuts import get_object_or_404
from django.db import transaction

from fiesta.models import (
    RegistroUsuario, Carrito, ItemCarrito, Servicio, Combo, Promocion,
    HorarioDisponible, Reserva, DetalleReserva, ConfiguracionPago
)
from fiesta.api.serializers.cart import CarritoSerializer, ItemCarritoSerializer
from fiesta.api.serializers.bookings import ConfiguracionPagoSerializer
from fiesta.api.utils import generar_codigo_reserva


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def agregar_al_carrito(request):
    """
    Agrega un producto (servicio, combo o promoción) al carrito del usuario.
    """
    print("--- INTENTO DE AGREGAR AL CARRITO ---")
    
    try:
        tipo = request.data.get('tipo')
        item_id = request.data.get('item_id')
        cantidad = int(request.data.get('cantidad', 1))

        if not tipo or not item_id:
            return Response({
                'error': 'Faltan datos: tipo o item_id requeridos'
            }, status=400)

        cliente = RegistroUsuario.objects.filter(email=request.user.email).first()
        if not cliente:
            return Response({
                'error': 'No se encontró tu perfil de cliente.'
            }, status=404)

        carrito, _ = Carrito.objects.get_or_create(cliente=cliente)

        servicio_obj = None
        combo_obj = None
        promocion_obj = None
        precio = 0

        if tipo == 'servicio':
            servicio_obj = get_object_or_404(Servicio, pk=item_id)
            precio = servicio_obj.precio_base
        elif tipo == 'combo':
            combo_obj = get_object_or_404(Combo, pk=item_id)
            precio = combo_obj.precio_combo
        elif tipo == 'promocion':
            promocion_obj = get_object_or_404(Promocion, pk=item_id)
            precio = promocion_obj.precio
        
        if not servicio_obj and not combo_obj and not promocion_obj:
            return Response({
                'error': 'Producto no encontrado'
            }, status=404)

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


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def confirmar_carrito(request):
    """
    Convierte el carrito en una reserva pendiente de pago.
    Valida fecha y dirección del evento.
    """
    print("--- CONFIRMANDO RESERVA ---")
    try:
        fecha_evento = request.data.get('fecha_evento')
        direccion = request.data.get('direccion_evento')
        
        if not fecha_evento or not direccion:
            return Response({
                'error': 'Fecha y dirección son obligatorias'
            }, status=400)

        cliente = RegistroUsuario.objects.filter(email=request.user.email).first()
        carrito = Carrito.objects.filter(cliente=cliente).first()

        if not carrito or not carrito.items.exists():
            return Response({
                'error': 'El carrito está vacío'
            }, status=400)

        subtotal_total = sum(item.subtotal for item in carrito.items.all())
        impuestos = float(subtotal_total) * 0.12
        total = float(subtotal_total) + impuestos

        horario = HorarioDisponible.objects.filter(fecha=fecha_evento).first()
        
        if not horario:
            return Response({
                'error': f'No hay disponibilidad abierta para el {fecha_evento}'
            }, status=400)

        overlap_carrito = Reserva.objects.filter(
            fecha_evento=fecha_evento,
            estado__in=['APROBADA', 'PENDIENTE']
        ).exists()
        
        if overlap_carrito:
            return Response({
                'error': 'Lo sentimos, este día ya ha sido reservado por otro usuario.'
            }, status=400)

        with transaction.atomic():
            nueva_reserva = Reserva.objects.create(
                cliente=cliente,
                horario=horario,
                codigo_reserva=generar_codigo_reserva(),
                fecha_evento=fecha_evento,
                fecha_inicio=horario.hora_inicio,
                direccion_evento=direccion,
                subtotal=subtotal_total,
                impuestos=impuestos,
                total=total,
                estado='PENDIENTE'
            )

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
                    print(f"DEBUG: Detalle creado ID={detalle.id} | Tipo={detalle.tipo}")
                except Exception as e:
                    print(f"DEBUG ERROR creando detalle: {e}")
                    raise e
            
            carrito.items.all().delete()

            try:
                detalles_memoria = []
                for item in carrito.items.all():
                    tipo_char = 'S' if item.servicio else ('C' if item.combo else 'P')
                    nombre = item.servicio.nombre if item.servicio else (item.combo.nombre if item.combo else item.promocion.nombre)
                    detalles_memoria.append({
                        'nombre': nombre,
                        'cantidad': item.cantidad,
                        'subtotal': item.subtotal
                    })
                
                # Enviar correo de reserva
                from fiesta.api.views.bookings import enviar_correo_reserva
                enviar_correo_reserva(nueva_reserva.id, detalles_previa_carga=detalles_memoria)
            except Exception as e:
                print(f"⚠️ Error enviando correo: {e}")

        return Response({
            'mensaje': 'Reserva creada con éxito', 
            'codigo': nueva_reserva.codigo_reserva
        }, status=201)

    except Exception as e:
        print(f"ERROR CONFIRMACION: {str(e)}")
        traceback.print_exc()
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def checkout_pago(request, reserva_id):
    """
    Endpoint para que el usuario elija método de pago y suba comprobante si es necesario.
    """
    reserva = get_object_or_404(Reserva, id=reserva_id, cliente__email=request.user.email)
    
    metodo = request.data.get('metodo_pago')
    if metodo not in ['transferencia', 'tarjeta', 'efectivo']:
        return Response({
            'error': 'Método de pago no válido'
        }, status=400)
    
    reserva.metodo_pago = metodo
    
    if metodo == 'transferencia':
        comprobante = request.FILES.get('comprobante_pago')
        if comprobante:
            reserva.comprobante_pago = comprobante
    elif metodo == 'tarjeta':
        transaccion_id = request.data.get('transaccion_id')
        if transaccion_id:
            reserva.transaccion_id = transaccion_id
    elif metodo == 'efectivo':
        reserva.comprobante_pago = None
        reserva.transaccion_id = None
        
    reserva.save()
    
    response_data = {
        'mensaje': f'Método de pago {metodo} configurado correctamente',
        'metodo_pago': reserva.metodo_pago,
        'estado': reserva.estado
    }

    if metodo == 'transferencia':
        bancos = ConfiguracionPago.objects.filter(activo=True)
        response_data['bancos'] = ConfiguracionPagoSerializer(bancos, many=True).data

    return Response(response_data, status=200)


class CarritoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para visualizar carrito del usuario autenticado.
    Solo lectura (no permite modificar desde aquí, usar agregar_al_carrito).
    """
    queryset = Carrito.objects.all()
    serializer_class = CarritoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            # Buscar por email del User autenticado
            cliente = RegistroUsuario.objects.filter(email=user.email).first()
            if cliente:
                return Carrito.objects.filter(cliente=cliente)
        return Carrito.objects.none()


class ItemCarritoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar items individuales del carrito.
    Permite crear, actualizar y eliminar items del carrito del usuario.
    """
    queryset = ItemCarrito.objects.all()
    serializer_class = ItemCarritoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return ItemCarrito.objects.filter(carrito__cliente__email=self.request.user.email)
        return ItemCarrito.objects.none()
