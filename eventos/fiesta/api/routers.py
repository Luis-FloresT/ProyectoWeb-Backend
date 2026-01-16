from rest_framework.routers import DefaultRouter
from fiesta.api.views import (
    RegistroUsuarioViewSet, CategoriaViewSet, PromocionViewSet,
    ServicioViewSet, ComboViewSet, ComboServicioViewSet,
    HorarioDisponibleViewSet, ReservaViewSet, DetalleReservaViewSet,
    PagoViewSet, CancelacionViewSet, ConfiguracionPagoViewSet,
    CarritoViewSet, ItemCarritoViewSet,
)

router = DefaultRouter()

# Clientes
router.register(r'clientes', RegistroUsuarioViewSet, basename='cliente')

# Catálogo
router.register(r'categorias', CategoriaViewSet, basename='categoria')
router.register(r'promociones', PromocionViewSet, basename='promocion')
router.register(r'servicios', ServicioViewSet, basename='servicio')
router.register(r'combos', ComboViewSet, basename='combo')
router.register(r'combo-servicios', ComboServicioViewSet, basename='combo-servicio')

# Operaciones
router.register(r'horarios', HorarioDisponibleViewSet, basename='horario')
router.register(r'reservas', ReservaViewSet, basename='reserva')
router.register(r'detalles-reserva', DetalleReservaViewSet, basename='detalle-reserva')
router.register(r'pagos', PagoViewSet, basename='pago')
router.register(r'cancelaciones', CancelacionViewSet, basename='cancelacion')

# Carrito de compras
router.register(r'carritos', CarritoViewSet, basename='carrito')
router.register(r'items-carrito', ItemCarritoViewSet, basename='item-carrito')
router.register(r'bancos', ConfiguracionPagoViewSet, basename='configuracion-pago')

__all__ = ["router"]
