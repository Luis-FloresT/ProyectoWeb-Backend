import os
import django

# Configurar Django para poder usar settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eventos.settings")
django.setup()

from django.conf import settings
from django.core.mail import EmailMessage

# Usar la configuración de DEFAULT_FROM_EMAIL y el backend configurado
from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or settings.EMAIL_GMAIL.get('USERNAME')

email = EmailMessage(
    subject='Correo de prueba Django',
    body='Hola, este es un correo de prueba enviado desde Django',
    from_email=from_email,
    to=['tu_correo_de_prueba@example.com'],  # Cambia aquí a tu correo real
)
email.content_subtype = "plain"

try:
    # Esto usará el EMAIL_BACKEND configurado en settings.py
    email.send(fail_silently=False)
    print("Correo procesado por el backend configurado ✅")
except Exception as e:
    print("Error al enviar correo:", e)
