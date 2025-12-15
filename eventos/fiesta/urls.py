from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    home, LoginView, RegistroUsuarioView, 
    RegistroUsuarioViewSet, CategoriaViewSet, PromocionViewSet, 
    ServicioViewSet, ComboViewSet, ComboServicioViewSet, 
    HorarioDisponibleViewSet, ReservaViewSet, DetalleReservaViewSet, 
    PagoViewSet, CancelacionViewSet,
    # Nuevas importaciones del carrito (ACTUALIZADO)
    CarritoViewSet, agregar_al_carrito, confirmar_carrito, ItemCarritoViewSet
)

router = DefaultRouter()

# 1. CLIENTES
router.register(r'clientes', RegistroUsuarioViewSet, basename='cliente')

# 2. CATÁLOGO
router.register(r'categorias', CategoriaViewSet, basename='categoria')
router.register(r'promociones', PromocionViewSet, basename='promocion')
router.register(r'servicios', ServicioViewSet, basename='servicio')
router.register(r'combos', ComboViewSet, basename='combo')
router.register(r'combo-servicios', ComboServicioViewSet, basename='combo-servicio')

# 3. OPERACIONES
router.register(r'horarios', HorarioDisponibleViewSet, basename='horario')
router.register(r'reservas', ReservaViewSet, basename='reserva')
router.register(r'detalles-reserva', DetalleReservaViewSet, basename='detalle-reserva')
router.register(r'pagos', PagoViewSet, basename='pago')
router.register(r'cancelaciones', CancelacionViewSet, basename='cancelacion')

# 4. CARRITO DE COMPRAS
router.register(r'carritos', CarritoViewSet, basename='carrito')
# Ruta necesaria para poder eliminar items individualmente (DELETE /items-carrito/{id}/)
router.register(r'items-carrito', ItemCarritoViewSet, basename='item-carrito')

urlpatterns = [
    path('', home, name='home'),
    path('login/', LoginView.as_view(), name='login'),
    path('registro/', RegistroUsuarioView.as_view(), name='registro_usuario'),
    
    # --- ENDPOINTS MANUALES DEL CARRITO ---
    
    # 1. Agregar (POST): Recibe { tipo, item_id, cantidad }
    path('carrito/agregar/', agregar_al_carrito, name='agregar_al_carrito'),
    
    # 2. Confirmar (POST): Convierte carrito en reserva
    path('carrito/confirmar/', confirmar_carrito, name='confirmar_carrito'),

    path('', include(router.urls)),
]