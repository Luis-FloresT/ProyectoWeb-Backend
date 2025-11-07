from rest_framework import routers
from django.urls import path, include
from .views import (
    RegistroUsuarioViewSet, CategoriaViewSet, PromocionViewSet,
    HorarioDisponibleViewSet, ServicioViewSet, ComboViewSet,
    ComboServicioViewSet, ReservaViewSet, DetalleReservaViewSet,
    PagoViewSet, CancelacionViewSet
)

router = routers.DefaultRouter()
router.register(r'usuarios', RegistroUsuarioViewSet)
router.register(r'categorias', CategoriaViewSet)
router.register(r'promociones', PromocionViewSet)
router.register(r'horarios', HorarioDisponibleViewSet)
router.register(r'servicios', ServicioViewSet)
router.register(r'combos', ComboViewSet)
router.register(r'combo-servicios', ComboServicioViewSet)
router.register(r'reservas', ReservaViewSet)
router.register(r'detalles-reserva', DetalleReservaViewSet)
router.register(r'pagos', PagoViewSet)
router.register(r'cancelaciones', CancelacionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
