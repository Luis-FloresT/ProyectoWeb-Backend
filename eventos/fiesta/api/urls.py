from django.urls import path, include
from fiesta.api.views import (
    # Auth
    LoginView, RegistroUsuarioView, VerificarEmailView,
    PasswordResetRequestView, PasswordResetConfirmView,
    # Cart manual endpoints
    agregar_al_carrito, confirmar_carrito, checkout_pago,
)
from fiesta.api.routers import router

urlpatterns = [
    # Auth
    path('login/', LoginView.as_view(), name='login'),
    path('registro/', RegistroUsuarioView.as_view(), name='registro_usuario'),
    path('verificar-email/', VerificarEmailView.as_view(), name='verificar_email'),

    # Carrito manual
    path('carrito/agregar/', agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/confirmar/', confirmar_carrito, name='confirmar_carrito'),
    path('checkout-pago/<int:reserva_id>/', checkout_pago, name='checkout_pago'),

    # Recuperación de contraseña
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # ViewSets
    path('', include(router.urls)),
]
