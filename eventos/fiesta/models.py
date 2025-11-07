from django.db import models


class RegistroUsuario(models.Model):
    """Corresponde a la tabla registro_usuario."""
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    contrasena = models.CharField(max_length=128)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Registro de Usuario"
        verbose_name_plural = "Registros de Usuarios"
        db_table = 'registro_usuario'

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.email})"


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
        return self.nombre


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
        return self.nombre


class Combo(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio_combo = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    imagen = models.URLField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    servicios = models.ManyToManyField('Servicio', through='ComboServicio', related_name='combos')
    promocion = models.ForeignKey('Promocion', on_delete=models.SET_NULL, null=True, blank=True, related_name='combos')

    class Meta:
        verbose_name = "Combo"
        verbose_name_plural = "Combos"
        db_table = 'combo'

    def __str__(self):
        return self.nombre


class ComboServicio(models.Model):
    combo = models.ForeignKey(Combo, on_delete=models.CASCADE)
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)
    
    class Meta:
        verbose_name = "Detalle Combo Servicio"
        verbose_name_plural = "Detalles Combo Servicio"
        db_table = 'combo_servicio'
        unique_together = ('combo', 'servicio')


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
        return f"{self.fecha} ({self.hora_inicio} - {self.hora_fin})"


class Reserva(models.Model):
    cliente = models.ForeignKey(RegistroUsuario, on_delete=models.PROTECT, related_name='reservas')
    horario = models.ForeignKey(HorarioDisponible, on_delete=models.PROTECT, related_name='reservas')
    
    codigo_reserva = models.CharField(max_length=50, unique=True)
    fecha_evento = models.DateField()
    fecha_inicio = models.TimeField()
    direccion_evento = models.CharField(max_length=255)
    notas_especiales = models.TextField(blank=True, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    impuestos = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=50, default='PENDIENTE')
    fecha_reserva = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        db_table = 'reserva'

    def __str__(self):
        return f"Reserva {self.codigo_reserva} - Cliente: {self.cliente.email}"


class DetalleReserva(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='detalles')
    combo = models.ForeignKey(Combo, on_delete=models.SET_NULL, null=True, blank=True)
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    
    TIPO_CHOICES = [
        ('C', 'Combo'),
        ('S', 'Servicio'),
    ]
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES)
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Detalle de Reserva"
        verbose_name_plural = "Detalles de Reserva"
        db_table = 'detalle_reserva'

    def __str__(self):
        return f"Detalle de Reserva {self.reserva.codigo_reserva} - Tipo: {self.tipo}"


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
        return f"Pago de Reserva {self.reserva.codigo_reserva} - Estado: {self.estado_pago}"


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
        return f"Cancelación de Reserva {self.reserva.codigo_reserva}"
