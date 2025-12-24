from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
<<<<<<< HEAD
from django.utils import timezone
=======
from django.utils import timezone  # Para timezone.now()
>>>>>>> main
from datetime import timedelta
import uuid

# ==========================================
# 1. GESTIÓN DE USUARIOS Y CLIENTES
# ==========================================

class RegistroUsuario(models.Model):
    """
    Cliente externo que realiza la reserva.
<<<<<<< HEAD
    Separado del User de Django para no mezclar auth interna con datos de clientes.
    """
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    contrasena = models.CharField(max_length=128)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    
=======
    Combina información del cliente y se relaciona con el User de Django.
    """
    # Relación de la rama 'feature/modificación' (es la correcta para un perfil)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil", null=True, blank=True)
    
    # Campos de cliente (De tu rama 'HEAD')
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    email = models.EmailField(unique=True, null=True, blank=True) # <-- Reincorporado
    contrasena = models.CharField(max_length=128, null=True, blank=True) # <-- Reincorporado (Aunque no se usa para login con User de Django)
    telefono = models.CharField(max_length=20, unique=True)
    activo = models.BooleanField(default=True) # <-- Reincorporado
    fecha_registro = models.DateTimeField(auto_now_add=True)

>>>>>>> main
    class Meta:
        verbose_name = "Registro de Usuario"
        verbose_name_plural = "Registros de Usuarios"
        db_table = 'registro_usuario'

    def __str__(self):
<<<<<<< HEAD
        return f"{self.nombre} {self.apellido} | {self.email}"


class EmailVerificationToken(models.Model):
    """
    Token para verificación de correo electrónico.
    Se crea al registrarse y expira en 24 horas.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_tokens')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = "Token de Verificación de Email"
        verbose_name_plural = "Tokens de Verificación de Email"
        db_table = 'email_verification_token'

=======
        # Usamos el string más descriptivo
        return f"{self.nombre} {self.apellido} ({self.email or self.user.email if self.user else 'No asociado'})"


# ---------------------------
# MODELO DE VERIFICACIÓN DE EMAIL (De la rama 'feature/modificación')
# ---------------------------

class EmailVerificationToken(models.Model):
    """Token de verificación de correo."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_tokens")
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

>>>>>>> main
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
<<<<<<< HEAD
        return f"Token for {self.user.username} - {self.token[:10]}..."
=======
        return f"{self.user.username} - {self.token}"
>>>>>>> main


# ==========================================
# 2. CATÁLOGO (Servicios, Combos, Promos)
# ==========================================

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        db_table = 'categoria'

    def __str__(self):
        return self.nombre


class Promocion(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    descuento_monto = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Promoción"
        verbose_name_plural = "Promociones"
        db_table = 'promocion'

    def __str__(self):
        return f"{self.nombre} ({self.descuento_porcentaje}% / ${self.descuento_monto})"


<<<<<<< HEAD
=======
# ---------------------------
# MODELOS DE SERVICIOS Y COMBOS
# ---------------------------

>>>>>>> main
class Servicio(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='servicios')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)
    duracion_horas = models.DecimalField(max_digits=5, decimal_places=2)
    capacidad_persona = models.IntegerField()
    imagen = models.URLField(blank=True, null=True)
    disponible = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        db_table = 'servicio'

    def __str__(self):
        return f"{self.nombre} - ${self.precio_base}"


class Combo(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio_combo = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    imagen = models.URLField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    servicios = models.ManyToManyField('Servicio', through='ComboServicio', related_name='combos')
    promocion = models.ForeignKey(Promocion, on_delete=models.SET_NULL, null=True, blank=True, related_name='combos')

    class Meta:
        verbose_name = "Combo"
        verbose_name_plural = "Combos"
        db_table = 'combo'

    def __str__(self):
        return f"{self.nombre} - ${self.precio_combo}"


class ComboServicio(models.Model):
    combo = models.ForeignKey(Combo, on_delete=models.CASCADE)
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)
    
    class Meta:
        verbose_name = "Detalle Combo Servicio"
        verbose_name_plural = "Detalles Combo Servicio"
        db_table = 'combo_servicio'
        unique_together = ('combo', 'servicio')


# ==========================================
<<<<<<< HEAD
# 4. GESTIÓN DEL CARRITO
# ==========================================

class Carrito(models.Model):
    """
    Carrito temporal asociado a un cliente registrado.
    """
    cliente = models.OneToOneField(RegistroUsuario, on_delete=models.CASCADE, related_name='carrito')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Carrito de Compras"
        verbose_name_plural = "Carritos de Compras"
        db_table = 'carrito'

    def __str__(self):
        return f"Carrito de {self.cliente.nombre}"

class ItemCarrito(models.Model):
    """
    Items individuales dentro del carrito. 
    Puede ser un Servicio O un Combo.
    """
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    
    # Opcionales: El item puede ser servicio, combo O promoción
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    combo = models.ForeignKey(Combo, on_delete=models.SET_NULL, null=True, blank=True)
    promocion = models.ForeignKey(Promocion, on_delete=models.SET_NULL, null=True, blank=True)
    
    cantidad = models.PositiveIntegerField(default=1)
    # Guardamos el precio al momento de añadirlo por si cambia después
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 

    class Meta:
        verbose_name = "Item del Carrito"
        verbose_name_plural = "Items del Carrito"
        db_table = 'item_carrito'

    def __str__(self):
        nombre = "Item desconocido"
        if self.combo:
            nombre = self.combo.nombre
        elif self.servicio:
            nombre = self.servicio.nombre
        elif self.promocion:
            nombre = self.promocion.nombre
        return f"{nombre} (x{self.cantidad})"
        
    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad


# ==========================================
=======
>>>>>>> main
# 3. GESTIÓN DE EVENTOS (Reservas, Pagos)
# ==========================================

class HorarioDisponible(models.Model):
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    disponible = models.BooleanField(default=True)
    capacidad_reserva = models.IntegerField()

    class Meta:
        verbose_name = "Horario Disponible"
        verbose_name_plural = "Horarios Disponibles"
        db_table = 'horario_disponible'
        unique_together = ('fecha', 'hora_inicio', 'hora_fin')

    def __str__(self):
        return f"{self.fecha} | {self.hora_inicio} - {self.hora_fin}"


<<<<<<< HEAD
class ConfiguracionPago(models.Model):
    """
    Datos de cuentas bancarias para transferencias (Ej: Banco Guayaquil, Pichincha).
    """
    banco_nombre = models.CharField(max_length=100)
    ruc = models.CharField(max_length=20)
    tipo_cuenta = models.CharField(max_length=50) # Ej: Ahorros, Corriente
    numero_cuenta = models.CharField(max_length=50)
    beneficiario = models.CharField(max_length=100, default='Burbujitas de Colores')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Configuración de Pago"
        verbose_name_plural = "Configuraciones de Pago"
        db_table = 'configuracion_pago'

    def __str__(self):
        return f"{self.banco_nombre} - {self.numero_cuenta}"


class Reserva(models.Model):
    METODO_PAGO_CHOICES = [
        ('transferencia', 'Transferencia'),
        ('tarjeta', 'Tarjeta'),
        ('efectivo', 'Efectivo'),
    ]

    ESTADO_RESERVA_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADA', 'Aprobada'),
        ('ANULADA', 'Anulada'),
    ]

=======
class Reserva(models.Model):
>>>>>>> main
    cliente = models.ForeignKey(RegistroUsuario, on_delete=models.PROTECT, related_name='reservas')
    horario = models.ForeignKey(HorarioDisponible, on_delete=models.PROTECT, related_name='reservas')
    
    codigo_reserva = models.CharField(max_length=50, unique=True)
    fecha_evento = models.DateField()
    fecha_inicio = models.TimeField()
    direccion_evento = models.CharField(max_length=255)
    notas_especiales = models.TextField(blank=True, null=True)
    
<<<<<<< HEAD
    # Pago y comprobante
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default='transferencia')
    comprobante_pago = models.ImageField(upload_to='comprobantes/', null=True, blank=True)
    transaccion_id = models.CharField(max_length=100, null=True, blank=True, help_text="ID devuelto por la pasarela (Payphone, Stripe, etc)")

=======
>>>>>>> main
    # Datos financieros
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    impuestos = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
<<<<<<< HEAD
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_RESERVA_CHOICES, 
        default='PENDIENTE'
    )
=======
    estado = models.CharField(max_length=50, default='PENDIENTE') # PENDIENTE, CONFIRMADA, CANCELADA
>>>>>>> main
    fecha_reserva = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        db_table = 'reserva'
        ordering = ['-fecha_reserva']

    def __str__(self):
        return f"#{self.codigo_reserva} - {self.fecha_evento} ({self.estado})"


class DetalleReserva(models.Model):
    TIPO_CHOICES = [
        ('C', 'Combo'),
        ('S', 'Servicio'),
<<<<<<< HEAD
        ('P', 'Promoción'),
=======
>>>>>>> main
    ]
    
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='detalles')
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES)
    
    # Relaciones opcionales dependiendo del tipo
    combo = models.ForeignKey(Combo, on_delete=models.SET_NULL, null=True, blank=True)
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
<<<<<<< HEAD
    promocion = models.ForeignKey(Promocion, on_delete=models.SET_NULL, null=True, blank=True)
=======
>>>>>>> main
    
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Detalle de Reserva"
        verbose_name_plural = "Detalles de Reserva"
        db_table = 'detalle_reserva'

    def __str__(self):
<<<<<<< HEAD
        item_nombre = "Item eliminado"
        if self.combo:
            item_nombre = self.combo.nombre
        elif self.servicio:
            item_nombre = self.servicio.nombre
        elif self.promocion:
            item_nombre = self.promocion.nombre
        return f"{self.reserva.codigo_reserva}: {item_nombre} x{self.cantidad}"


=======
        item_nombre = self.combo.nombre if self.combo else (self.servicio.nombre if self.servicio else "Item eliminado")
        return f"{self.reserva.codigo_reserva}: {item_nombre} x{self.cantidad}"


# ---------------------------
# MODELOS DE PAGO Y CANCELACIÓN
# ---------------------------

>>>>>>> main
class Pago(models.Model):
    reserva = models.OneToOneField(Reserva, on_delete=models.PROTECT, related_name='pago')
    metodo_pago = models.CharField(max_length=50)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    estado_pago = models.CharField(max_length=50, default='PENDIENTE')
    fecha_pago = models.DateTimeField(auto_now_add=True)
    comprobante = models.URLField(blank=True, null=True)
    notas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        db_table = 'pago'

    def __str__(self):
        return f"Pago {self.reserva.codigo_reserva} - ${self.monto}"


class Cancelacion(models.Model):
    reserva = models.OneToOneField(Reserva, on_delete=models.CASCADE, related_name='cancelacion')
    motivo = models.TextField()
    fecha_cancelacion = models.DateTimeField(auto_now_add=True)
    monto_personalizado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    reembolso_aplicado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fecha_reembolso = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Cancelación"
        verbose_name_plural = "Cancelaciones"
        db_table = 'cancelacion'

    def __str__(self):
        return f"Cancelación #{self.reserva.codigo_reserva}"

<<<<<<< HEAD
=======

# ==========================================
# 4. GESTIÓN DEL CARRITO (De la rama 'HEAD')
# ==========================================

class Carrito(models.Model):
    """
    Carrito temporal asociado a un cliente registrado.
    """
    cliente = models.OneToOneField(RegistroUsuario, on_delete=models.CASCADE, related_name='carrito')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Carrito de Compras"
        verbose_name_plural = "Carritos de Compras"
        db_table = 'carrito'

    def __str__(self):
        return f"Carrito de {self.cliente.nombre}"

class ItemCarrito(models.Model):
    """
    Items individuales dentro del carrito. 
    Puede ser un Servicio O un Combo.
    """
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    
    # Opcionales: El item puede ser servicio O combo
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    combo = models.ForeignKey(Combo, on_delete=models.SET_NULL, null=True, blank=True)
    
    cantidad = models.PositiveIntegerField(default=1)
    # Guardamos el precio al momento de añadirlo por si cambia después
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 

    class Meta:
        verbose_name = "Item del Carrito"
        verbose_name_plural = "Items del Carrito"
        db_table = 'item_carrito'

    def __str__(self):
        nombre = self.combo.nombre if self.combo else (self.servicio.nombre if self.servicio else "Item desconocido")
        return f"{nombre} (x{self.cantidad})"
        
    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad


>>>>>>> main
# ==========================================
# 5. SEÑALES (AUTOMATIZACIÓN DE PERFILES)
# ==========================================

@receiver(post_save, sender=User)
def crear_perfil_cliente_automatico(sender, instance, created, **kwargs):
    """
<<<<<<< HEAD
    Esta función se ejecuta AUTOMÁTICAMENTE cada vez que se crea un Usuario de Django
    (sea por comando createsuperuser, por admin o por registro normal).
    
    Si el usuario es nuevo, le crea su perfil en RegistroUsuario para que pueda comprar.
    """
    if created:
        # Verificamos si ya tiene perfil (por si acaso)
        if not RegistroUsuario.objects.filter(email=instance.email).exists():
            RegistroUsuario.objects.create(
                nombre=instance.username,
                apellido="Admin" if instance.is_staff else "",
                email=instance.email,
                # Generamos un teléfono falso único para que no falle la validación
                telefono=f"000-{uuid.uuid4().hex[:8]}", 
                contrasena="admin_pass_encrypted", # No relevante para superusers
                activo=True
            )
            print(f"--- Perfil de cliente creado automáticamente para: {instance.username} ---")

# ==========================================
# 4. SIGNALS (Automatización)
# ==========================================

@receiver(post_save, sender=Reserva)
def auto_confirmacion_pago(sender, instance, created, **kwargs):
    """
    Detecta cambios de estado y envía correos automatizados.
    Silencioso al crear (PENDIENTE). Solo dispara con APROBADA o ANULADA.
    """
    from .views import enviar_correo_confirmacion, enviar_correo_anulacion
    
    # 1. CASO: APROBADA (Solo si pasamos de PENDIENTE a APROBADA)
    # Usamos fecha_confirmacion como candado para evitar duplicados
    if instance.estado == 'APROBADA' and instance.fecha_confirmacion is None:
        # Marcamos la fecha de confirmación inmediatamente
        sender.objects.filter(id=instance.id).update(fecha_confirmacion=timezone.now())
        
        # Enviar doble notificación (Cliente + Admin)
        enviar_correo_confirmacion(instance.id)

    # 2. CASO: ANULADA
    if instance.estado == 'ANULADA':
        enviar_correo_anulacion(instance.id)
=======
    Crea un perfil de RegistroUsuario si se crea un nuevo User de Django
    y ese usuario aún no tiene un perfil asociado.
    """
    if created:
        # Usa el try/except para manejar si el perfil ya fue creado por el proceso de registro.
        try:
            # Si instance.perfil ya existe, no hacemos nada (el perfil se creó desde la vista)
            _ = instance.perfil
        except RegistroUsuario.DoesNotExist:
            # Si el perfil NO existe (típicamente si se crea desde el admin o shell)
            RegistroUsuario.objects.create(
                user=instance, # Enlaza el User correctamente
                nombre=instance.username,
                apellido="Admin" if instance.is_staff else "",
                email=instance.email, # Usamos el email del User
                # Generamos un teléfono falso único para que no falle la validación
                telefono=f"000-{uuid.uuid4().hex[:8]}", 
                activo=True
            )
            print(f"--- Perfil de cliente creado automáticamente para: {instance.username} ---")
>>>>>>> main
