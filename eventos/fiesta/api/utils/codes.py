import random
import uuid


def generar_codigo_reserva():
    """Genera un código único para una reserva (RES-XXXX-YYYY)."""
    return f"RES-{random.randint(1000, 9999)}-{uuid.uuid4().hex[:4].upper()}"
