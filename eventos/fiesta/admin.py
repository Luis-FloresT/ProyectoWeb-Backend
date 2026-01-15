from django.contrib import admin
from .models import (
    RegistroUsuario, Categoria, Promocion, Servicio, Combo, ComboServicio,
    HorarioDisponible, Reserva, DetalleReserva, Pago, Cancelacion,
    Carrito, ItemCarrito, ConfiguracionPago  # <--- AGREGADOS AQUÍ
)

# ==========================================
# USUARIOS
# ==========================================

@admin.register(RegistroUsuario)
class RegistroUsuarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'apellido', 'email', 'telefono', 'creado_en', 'activo')
    search_fields = ('nombre', 'email', 'telefono')
    list_filter = ('activo', 'creado_en')

# ==========================================
# CATÁLOGO
# ==========================================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo')

@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio_base', 'duracion_horas', 'disponible')
    list_filter = ('categoria', 'disponible')
    search_fields = ('nombre',)

class ComboServicioInline(admin.TabularInline):
    model = ComboServicio
    extra = 1

@admin.register(Combo)
class ComboAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_combo', 'activo')
    inlines = [ComboServicioInline]

@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_inicio', 'fecha_fin', 'activo')
    list_filter = ('activo', 'fecha_inicio')

# ==========================================
# NEGOCIO (RESERVAS)
# ==========================================

@admin.register(HorarioDisponible)
class HorarioDisponibleAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'hora_inicio', 'hora_fin', 'disponible', 'capacidad_reserva')
    list_filter = ('fecha', 'disponible')

class DetalleReservaInline(admin.TabularInline):
    model = DetalleReserva
    extra = 0
    readonly_fields = ('subtotal',)

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('codigo_reserva', 'cliente', 'fecha_evento', 'estado', 'total')
    list_filter = ('estado', 'fecha_evento', 'creado_en')
    search_fields = ('codigo_reserva', 'cliente__nombre', 'cliente__email')
    inlines = [DetalleReservaInline]
    date_hierarchy = 'fecha_evento'

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('reserva', 'monto', 'metodo_pago', 'estado_pago', 'creado_en')
    list_filter = ('estado_pago', 'metodo_pago')
    search_fields = ('reserva__codigo_reserva',)

@admin.register(Cancelacion)
class CancelacionAdmin(admin.ModelAdmin):
    list_display = ('reserva', 'creado_en', 'reembolso_aplicado')

@admin.register(ConfiguracionPago)
class ConfiguracionPagoAdmin(admin.ModelAdmin):
    list_display = ('banco_nombre', 'numero_cuenta', 'tipo_cuenta', 'activo')
    list_filter = ('activo',)
    search_fields = ('banco_nombre', 'numero_cuenta')

# ==========================================
# GESTIÓN DEL CARRITO (NUEVO)
# ==========================================

class ItemCarritoInline(admin.TabularInline):
    """
    Permite ver los productos dentro del carrito directamente.
    """
    model = ItemCarrito
    extra = 0
    readonly_fields = ('subtotal',) # El subtotal es calculado, mejor solo lectura

@admin.register(Carrito)
class CarritoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'creado_en', 'actualizado_en')
    search_fields = ('cliente__nombre', 'cliente__email')
    list_filter = ('actualizado_en',)
    inlines = [ItemCarritoInline] # Conecta los items al carrito

@admin.register(ItemCarrito)
class ItemCarritoAdmin(admin.ModelAdmin):
    """
    Vista individual de items por si necesitas buscar algo específico fuera de un carrito.
    """
    list_display = ('id', 'carrito', 'servicio', 'combo', 'cantidad', 'subtotal')
    search_fields = ('carrito__cliente__email', 'servicio__nombre', 'combo__nombre')