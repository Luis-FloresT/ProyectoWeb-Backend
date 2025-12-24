import os
import django
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventos.settings')
django.setup()

from fiesta.models import Reserva, DetalleReserva

def debug_latest_reserva():
    print("--- INICIO DEPURACION ---")
    try:
        last_reserva = Reserva.objects.last()
        if not last_reserva:
            print("No hay reservas en la base de datos.")
            return

        print(f"Ultima Reserva: {last_reserva} (ID: {last_reserva.id})")
        print(f"Cliente: {last_reserva.cliente}")
        
        detalles = last_reserva.detalles.all()
        print(f"Cantidad de detalles asociados: {detalles.count()}")
        
        if detalles.count() == 0:
            print("!!! ALERTA: La reserva no tiene detalles.")
        
        for i, d in enumerate(detalles):
            print(f" [Detalle #{i+1}] ID: {d.id}")
            print(f"   - Tipo: {d.tipo}")
            
            # Verificar Combo
            if d.combo:
                print(f"   - Combo FK detectado: {d.combo} | ID: {d.combo.id} | Nombre: '{d.combo.nombre}'")
            else:
                print("   - Combo FK: None")
                
            # Verificar Servicio
            if d.servicio:
                print(f"   - Servicio FK detectado: {d.servicio} | Nombre: '{d.servicio.nombre}'")
            else:
                print("   - Servicio FK: None")
                
            # Verificar Promocion
            if d.promocion:
                print(f"   - Promocion FK detectado: {d.promocion} | Nombre: '{d.promocion.nombre}'")
            else:
                print("   - Promocion FK: None")

    except Exception as e:
        print(f"Error durante depuración: {e}")
    print("--- FIN DEPURACION ---")

if __name__ == "__main__":
    debug_latest_reserva()
