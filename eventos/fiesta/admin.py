from django.contrib import admin
from .models import (
    Categoria, Promocion, RegistroUsuario, HorarioDisponible,
    Combo, Reserva, Pago, Cancelacion, Servicio, DetalleReserva, ComboServicio
)

admin.site.register(Categoria)
admin.site.register(Promocion)
admin.site.register(RegistroUsuario)
admin.site.register(HorarioDisponible)
admin.site.register(Combo)
admin.site.register(Reserva)
admin.site.register(Pago)
admin.site.register(Cancelacion)
admin.site.register(Servicio)
admin.site.register(DetalleReserva)
admin.site.register(ComboServicio)

