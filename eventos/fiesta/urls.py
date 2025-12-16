from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    home, 
    LoginView, 
    RegistroUsuarioView, 
    # Vistas de Email/Verificación añadidas
    VerificarEmailView, 
    SendTestEmailView,
    
    # ViewSets de Catálogo y Usuarios
    RegistroUsuarioViewSet, 
    CategoriaViewSet, 
    PromocionViewSet, 
    ServicioViewSet, 
    ComboViewSet, 
    ComboServicioViewSet, 
    
    # ViewSets de Operaciones
    HorarioDisponibleViewSet, 
    ReservaViewSet, 
    DetalleReservaViewSet, 
    PagoViewSet, 
    CancelacionViewSet,
    
    # ViewSets y Funciones del Carrito
    CarritoViewSet, 
    agregar_al_carrito, 
    confirmar_carrito, 
    ItemCarritoViewSet
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
router.register(r'items-carrito', ItemCarritoViewSet, basename='item-carrito')


# URLs principales
urlpatterns = [
    path('', home, name='home'),
    path('login/', LoginView.as_view(), name='login'),
    path('registro/', RegistroUsuarioView.as_view(), name='registro_usuario'),
    
    # --- ENDPOINTS DE EMAIL/VERIFICACIÓN ---
    path('verificar-email/', VerificarEmailView.as_view(), name='verificar_email'),
    path('send-test-email/', SendTestEmailView.as_view(), name='send_test_email'), 
    
    # --- ENDPOINTS MANUALES DEL CARRITO ---
    path('carrito/agregar/', agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/confirmar/', confirmar_carrito, name='confirmar_carrito'),

    path('', include(router.urls)),
]