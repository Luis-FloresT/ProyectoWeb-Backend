from django.http import HttpResponse

def home(request):
    return HttpResponse("Bienvenido al sistema de eventos y fiestas 🎉")


from rest_framework import viewsets
from .models import (
    RegistroUsuario, Promocion, Categoria, Servicio, Combo, ComboServicio,
    HorarioDisponible, Reserva, DetalleReserva, Pago, Cancelacion
)
from .serializers import (
    RegistroUsuarioSerializer, PromocionSerializer, CategoriaSerializer,
    ServicioSerializer, ComboDetailSerializer, HorarioDisponibleSerializer,
    ReservaSerializer, DetalleReservaSerializer, PagoSerializer, CancelacionSerializer,
    ComboServicioSerializer
)


class RegistroUsuarioViewSet(viewsets.ModelViewSet):
    queryset = RegistroUsuario.objects.all()
    serializer_class = RegistroUsuarioSerializer


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer


class PromocionViewSet(viewsets.ModelViewSet):
    queryset = Promocion.objects.all()
    serializer_class = PromocionSerializer


class HorarioDisponibleViewSet(viewsets.ModelViewSet):
    queryset = HorarioDisponible.objects.all()
    serializer_class = HorarioDisponibleSerializer


class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer


class CancelacionViewSet(viewsets.ModelViewSet):
    queryset = Cancelacion.objects.all()
    serializer_class = CancelacionSerializer


class ServicioViewSet(viewsets.ModelViewSet):
    queryset = Servicio.objects.select_related('categoria').all()
    serializer_class = ServicioSerializer


class ComboServicioViewSet(viewsets.ModelViewSet):
    queryset = ComboServicio.objects.select_related('combo', 'servicio').all()
    serializer_class = ComboServicioSerializer


class ComboViewSet(viewsets.ModelViewSet):
    queryset = Combo.objects.select_related('promocion').prefetch_related('servicios').all()
    serializer_class = ComboDetailSerializer


class ReservaViewSet(viewsets.ModelViewSet):
    queryset = Reserva.objects.select_related('cliente', 'horario').all()
    serializer_class = ReservaSerializer


class DetalleReservaViewSet(viewsets.ModelViewSet):
    queryset = DetalleReserva.objects.select_related('reserva', 'combo', 'servicio').all()
    serializer_class = DetalleReservaSerializer
