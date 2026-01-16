"""
views.py - Archivo de compatibilidad

Este archivo mantiene compatibilidad hacia atrás. Las vistas han sido 
refactorizado en una estructura modular dentro de la carpeta 'api/':

├── api/
│   ├── permissions/        # Permisos personalizados
│   ├── serializers/        # Serializadores de modelos
│   ├── utils/              # Funciones auxiliares
│   └── views/              # Vistas organizadas por funcionalidad
│       ├── auth.py         # Autenticación
│       ├── catalog.py      # Catálogo de productos
│       ├── bookings.py     # Gestión de reservas
│       └── cart.py         # Carrito de compras

Importamos desde la nueva estructura para mantener compatibilidad
con código existente que pueda importar desde views.py
"""

# Re-exportar todas las vistas, permisos y utilidades desde la nueva estructura
from fiesta.api.views import (
    # Auth
    LoginView, RegistroUsuarioView, SendTestEmailView,
    VerificarEmailView, PasswordResetRequestView, PasswordResetConfirmView,
    
    # Catalog
    RegistroUsuarioViewSet, CategoriaViewSet, PromocionViewSet,
    ServicioViewSet, ComboViewSet, ComboServicioViewSet,
    
    # Bookings
    HorarioDisponibleViewSet, ReservaViewSet, DetalleReservaViewSet,
    PagoViewSet, CancelacionViewSet, ConfiguracionPagoViewSet,
    enviar_correo_reserva, enviar_correo_confirmacion,
    
    # Cart
    agregar_al_carrito, confirmar_carrito, checkout_pago,
    CarritoViewSet, ItemCarritoViewSet
)

from fiesta.api.permissions import SoloLecturaOAdmin, SoloUsuariosAutenticados
from fiesta.api.utils import (
    run_in_background, enviar_correo, generar_codigo_reserva, limpiar_texto
)

__all__ = [
    # Auth
    'LoginView', 'RegistroUsuarioView', 'SendTestEmailView',
    'VerificarEmailView', 'PasswordResetRequestView', 'PasswordResetConfirmView',
    
    # Catalog
    'RegistroUsuarioViewSet', 'CategoriaViewSet', 'PromocionViewSet',
    'ServicioViewSet', 'ComboViewSet', 'ComboServicioViewSet',
    
    # Bookings
    'HorarioDisponibleViewSet', 'ReservaViewSet', 'DetalleReservaViewSet',
    'PagoViewSet', 'CancelacionViewSet', 'ConfiguracionPagoViewSet',
    'enviar_correo_reserva', 'enviar_correo_confirmacion',
    
    # Cart
    'agregar_al_carrito', 'confirmar_carrito', 'checkout_pago',
    'CarritoViewSet', 'ItemCarritoViewSet',
    
    # Permissions & Utils
    'SoloLecturaOAdmin', 'SoloUsuariosAutenticados',
    'run_in_background', 'enviar_correo', 'generar_codigo_reserva', 'limpiar_texto'
]
