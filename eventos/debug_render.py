import os
import django
from django.template.loader import render_to_string
from django.conf import settings

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eventos.settings")
django.setup()

# Mock Objects
class MockCliente:
    nombre = "Juan"
    email = "test@example.com"

class MockReserva:
    codigo_reserva = "ABC-123"
    fecha_evento = "2025-10-10"
    direccion_evento = "Calle Falsa 123"
    total = 150.00
    cliente = MockCliente()

detalles_items = [
    {
        'nombre': "Hora Loca",
        'descripcion': "Incluye globos y antifaces",
        'cantidad': 1,
        'precio_unitario': 100.00,
        'subtotal': 100.00
    },
    {
        'nombre': "Mago",
        'descripcion': "",
        'cantidad': 1,
        'precio_unitario': 50.00,
        'subtotal': 50.00
    }
]

context = {
    'reserva': MockReserva(),
    'detalles': detalles_items,
    'dominio': "http://localhost:8000"
}

print("--- RENDERING TEMPLATE ---")
try:
    html = render_to_string('fiesta/emails/cliente_exito_confirmacion.html', context)
    print("✅ Template rendered successfully!")
    print(f"Length: {len(html)} chars")
    # Write to file to inspect
    with open("debug_rendered_email.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved to debug_rendered_email.html")
except Exception as e:
    print(f"❌ ERROR RENDERING TEMPLATE: {e}")
