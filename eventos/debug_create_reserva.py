import os
import django
import sys
from datetime import date, time

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventos.settings')
django.setup()

from fiesta.models import (
    RegistroUsuario, Carrito, ItemCarrito, Combo, Servicio, 
    Reserva, DetalleReserva, HorarioDisponible
)
from django.db import transaction
import random
import uuid

def simulate_booking_flow():
    print("--- SIMULATING BOOKING FLOW ---")
    
    # 1. Get or Create a Test User
    cliente = RegistroUsuario.objects.first()
    if not cliente:
        print("ERROR: No clients found.")
        return
    print(f"Using client: {cliente.email}")

    # 2. Get or Create a Combo
    combo = Combo.objects.first()
    if not combo:
        print("ERROR: No combos found.")
        return
    print(f"Using combo: {combo.nombre}")

    # 3. Add to Cart (Clean cart first)
    carrito, _ = Carrito.objects.get_or_create(cliente=cliente)
    carrito.items.all().delete()
    
    ItemCarrito.objects.create(
        carrito=carrito,
        combo=combo,
        cantidad=1,
        precio_unitario=combo.precio_combo
    )
    print(f"Added item to cart. Items count: {carrito.items.count()}")

    # 4. Create Reservation (Mimic logic)
    fecha_evento = date.today()
    horario, _ = HorarioDisponible.objects.get_or_create(
        fecha=fecha_evento,
        hora_inicio=time(10,0),
        hora_fin=time(14,0),
        defaults={'disponible': True, 'capacidad_reserva': 5}
    )
    
    print("Starting transaction...")
    try:
        with transaction.atomic():
            subtotal_total = sum(item.subtotal for item in carrito.items.all())
            impuestos = float(subtotal_total) * 0.12
            total = float(subtotal_total) + impuestos

            nueva_reserva = Reserva.objects.create(
                cliente=cliente,
                horario=horario,
                codigo_reserva=f"TEST-{random.randint(1000,9999)}",
                fecha_evento=fecha_evento,
                fecha_inicio=horario.hora_inicio,
                direccion_evento="Test Address",
                subtotal=subtotal_total,
                impuestos=impuestos,
                total=total,
                estado='PENDIENTE'
            )
            print(f"Reserva created: {nueva_reserva.id}")

            count = 0
            for item in carrito.items.all():
                DetalleReserva.objects.create(
                    reserva=nueva_reserva,
                    tipo='C', 
                    combo=item.combo,
                    cantidad=item.cantidad,
                    precio_unitario=item.precio_unitario,
                    subtotal=item.subtotal
                )
                count += 1
            print(f"Details created: {count}")
            
            # Note: In real view, we delete items here.
            # carrito.items.all().delete() 
            
    except Exception as e:
        print(f"Transaction failed: {e}")
        return

    # 5. Verify Persistence
    print("--- VERIFICATION ---")
    saved_reserva = Reserva.objects.get(id=nueva_reserva.id)
    saved_detalles = saved_reserva.detalles.all()
    print(f"Saved Reserva ID: {saved_reserva.id}")
    print(f"Saved Details Count: {saved_detalles.count()}")
    for d in saved_detalles:
        print(f" - Detail Combo: {d.combo.nombre if d.combo else 'None'}")

if __name__ == "__main__":
    simulate_booking_flow()
