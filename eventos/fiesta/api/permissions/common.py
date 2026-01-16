from rest_framework.permissions import BasePermission, SAFE_METHODS


class SoloLecturaOAdmin(BasePermission):
    """Permite lectura a todos y escritura solo a administradores."""
    def has_permission(self, request, view):
        return (request.method in SAFE_METHODS or (request.user and request.user.is_staff))


class SoloUsuariosAutenticados(BasePermission):
    """Requiere que el usuario esté autenticado."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
