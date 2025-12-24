import os
import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eventos.settings")
django.setup()

print("--- DEBUG EMAIL SETTINGS ---")
print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"BREVO_API_KEY configured: {'YES' if getattr(settings, 'BREVO_API_KEY', '') else 'NO (Empty)'}")
if hasattr(settings, 'ANYMAIL'):
    print(f"ANYMAIL Config: {settings.ANYMAIL.keys()}")
else:
    print("ANYMAIL Config: Not Found")

print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
