from django.contrib import admin
from rest_framework import routers
from django.urls import path, include
from .views import (
    LoginView,
    RegistroUsuarioView,
    VerificarEmailView,  # ← Añadido
    SendTestEmailView,
    RegistroUsuarioViewSet,
    PromocionViewSet,
    CategoriaViewSet,
    ServicioViewSet,
    ComboViewSet,
    ComboServicioViewSet,
    HorarioDisponibleViewSet,
    ReservaViewSet,
    DetalleReservaViewSet,
    PagoViewSet,
    CancelacionViewSet
)

# Configuración del router
router = routers.DefaultRouter()
router.register(r'usuarios', RegistroUsuarioViewSet)
router.register(r'promociones', PromocionViewSet)
router.register(r'categorias', CategoriaViewSet) 
router.register(r'servicios', ServicioViewSet)
router.register(r'combos', ComboViewSet)
router.register(r'combo-servicio', ComboServicioViewSet)
router.register(r'horarios', HorarioDisponibleViewSet)
router.register(r'reservas', ReservaViewSet)
router.register(r'detalles', DetalleReservaViewSet)
router.register(r'pagos', PagoViewSet)
router.register(r'cancelaciones', CancelacionViewSet)

# URLs principales
urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', LoginView.as_view(), name='login'),
    path('registro/', RegistroUsuarioView.as_view(), name='registro_usuario'),
    path('verificar-email/', VerificarEmailView.as_view(), name='verificar_email'),  # ← Añadido
    path('send-test-email/', SendTestEmailView.as_view(), name='send_test_email'),
    path('', include(router.urls)),
]
