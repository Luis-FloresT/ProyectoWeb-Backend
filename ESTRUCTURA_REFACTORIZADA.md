# Estructura Refactorizada del Backend - API Burbujitas de Colores

## 📁 Organización de Carpetas

```
fiesta/
├── api/
│   ├── __init__.py                    # Documentación de estructura
│   ├── permissions/
│   │   ├── __init__.py               # Exporta permisos
│   │   └── custom_permissions.py     # Permisos personalizados
│   ├── serializers/
│   │   └── __init__.py               # Todos los serializadores
│   ├── utils/
│   │   └── __init__.py               # Funciones auxiliares (correo, helpers)
│   └── views/
│       ├── __init__.py               # Exporta todas las vistas
│       ├── auth.py                   # Autenticación y gestión de usuarios
│       ├── catalog.py                # Catálogo (Categorías, Servicios, Combos, etc)
│       ├── bookings.py               # Reservas y pagos
│       └── cart.py                   # Carrito de compras
├── views.py                          # Archivo de compatibilidad (re-exporta desde api/)
├── urls.py                           # Rutas actualizadas
├── models.py                         # Modelos Django
├── admin.py                          # Admin de Django
├── apps.py                           # Configuración de app
├── tests.py                          # Tests
└── migrations/                       # Migraciones de BD
```

## 🎯 Funcionalidades por Módulo

### `api/permissions/`
**Propósito**: Permisos personalizados para control de acceso

- `SoloLecturaOAdmin`: Permite lectura a todos, solo edición a admins
- `SoloUsuariosAutenticados`: Requiere autenticación

### `api/serializers/`
**Propósito**: Serializadores para serializar/deserializar modelos

Incluye:
- RegistroUsuarioSerializer
- CategoriaSerializer, PromocionSerializer, ServicioSerializer
- ComboDetailSerializer, ComboServicioSerializer
- HorarioDisponibleSerializer
- ReservaSerializer, DetalleReservaSerializer
- PagoSerializer, CancelacionSerializer
- ConfiguracionPagoSerializer
- CarritoSerializer, ItemCarritoSerializer

### `api/utils/`
**Propósito**: Funciones auxiliares reutilizables

- `run_in_background()`: Ejecuta funciones en threads
- `enviar_correo()`: Envía correos con múltiples proveedores
- `generar_codigo_reserva()`: Genera códigos únicos
- `limpiar_texto()`: Normaliza textos para email providers

### `api/views/auth.py`
**Propósito**: Autenticación y gestión de usuarios

Endpoints:
- `POST /login/`: Login de usuario
- `POST /registro/`: Registro de nuevo usuario
- `GET /verificar-email/?token=...`: Verificación de email
- `POST /password-reset/request/`: Solicitar reset de contraseña
- `POST /password-reset/confirm/`: Confirmar y cambiar contraseña

### `api/views/catalog.py`
**Propósito**: Gestión del catálogo de productos

ViewSets:
- `RegistroUsuarioViewSet`: CRUD de usuarios
- `CategoriaViewSet`: CRUD de categorías
- `PromocionViewSet`: CRUD de promociones
- `ServicioViewSet`: CRUD de servicios
- `ComboViewSet`: CRUD de combos
- `ComboServicioViewSet`: Relación combo-servicio

### `api/views/bookings.py`
**Propósito**: Gestión de reservas y pagos

ViewSets:
- `HorarioDisponibleViewSet`: Horarios disponibles
- `ReservaViewSet`: CRUD de reservas
- `DetalleReservaViewSet`: Detalles de reservas
- `PagoViewSet`: Gestión de pagos
- `CancelacionViewSet`: Cancelaciones
- `ConfiguracionPagoViewSet`: Datos bancarios (solo lectura)

Funciones especiales:
- `enviar_correo_reserva()`: Notificación de reserva (cliente + admin)
- `enviar_correo_confirmacion()`: Confirmación de reserva

### `api/views/cart.py`
**Propósito**: Gestión del carrito de compras

ViewSets:
- `CarritoViewSet`: Visualizar carrito (solo lectura)
- `ItemCarritoViewSet`: Gestionar items del carrito

Endpoints especiales:
- `POST /carrito/agregar/`: Agregar item al carrito
- `POST /carrito/confirmar/`: Convertir carrito en reserva
- `POST /checkout-pago/<id>/`: Procesar pago

## 🔄 Flujo de Importaciones

```
urls.py
  ↓
  ├→ from fiesta.api.views import ...
  │    ↓
  │    api/views/__init__.py
  │    ├→ from .auth import ...
  │    ├→ from .catalog import ...
  │    ├→ from .bookings import ...
  │    └→ from .cart import ...
  │
  └→ legacy support: from fiesta.views import ...
       ↓
       views.py (re-exporta desde fiesta.api.views)
```

## 📊 Comparación: Antes vs Después

### Antes (Monolítico)
- `views.py`: 1300+ líneas
- Todas las vistas en un archivo
- Difícil de mantener y escalable
- Difícil de localizar código específico

### Después (Modular)
- `api/views/auth.py`: ~350 líneas (Autenticación)
- `api/views/catalog.py`: ~100 líneas (Catálogo)
- `api/views/bookings.py`: ~450 líneas (Reservas)
- `api/views/cart.py`: ~250 líneas (Carrito)
- `api/permissions/`: ~30 líneas
- `api/utils/`: ~100 líneas
- `api/serializers/`: ~140 líneas

**Total**: Misma funcionalidad, mejor organización y mantenibilidad

## 🚀 Ventajas de la Nueva Estructura

1. **Separación de responsabilidades**: Cada módulo tiene una responsabilidad clara
2. **Fácil de mantener**: Cambios localizados en módulos específicos
3. **Reutilizable**: Funciones utilitarias y permisos centralizados
4. **Escalable**: Fácil agregar nuevas funcionalidades
5. **Testeable**: Módulos pequeños y independientes son más fáciles de testear
6. **Compatible**: El archivo `views.py` mantiene compatibilidad hacia atrás

## 📝 Notas de Migración

- El archivo `views.py` ahora es un archivo de compatibilidad que re-exporta desde `api/`
- Todas las URLs importan desde `fiesta.api.views`
- Los modelos y migraciones no fueron modificados
- La funcionalidad es idéntica, solo reorganizada

## 🔧 Próximas Mejoras

- Agregar más logging
- Tests unitarios para cada módulo
- Documentación de API con Swagger
- Rate limiting
- Cache de horarios disponibles
- Webhooks para notificaciones
