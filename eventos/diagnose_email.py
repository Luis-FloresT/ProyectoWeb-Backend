import os
import django
import sys
from django.conf import settings
from django.core.mail import send_mail

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eventos.settings")
django.setup()

# Redirect output to file
log_file = open("email_diagnosis.log", "w", encoding="utf-8")
original_stdout = sys.stdout
sys.stdout = log_file

print("--- DIAGNÓSTICO DE EMAIL ---")
print(f"1. BACKEND ACTIVO: {settings.EMAIL_BACKEND}")
print(f"2. REMITENTE (FROM): {settings.DEFAULT_FROM_EMAIL}")

api_key = getattr(settings, 'BREVO_API_KEY', '')
print(f"3. BREVO_API_KEY Detectada: {'SÍ' if api_key else 'NO'}")
if api_key:
    print(f"   Longitud de la clave: {len(api_key)}")
    print(f"   Inicio de la clave: {api_key[:8]}...")

print("\n--- INTENTO DE ENVÍO DE PRUEBA ---")
try:
    # Intenta enviar un correo simple
    result = send_mail(
        'Prueba de Diagnóstico - ProyectoWeb',
        'Este es un correo de prueba para verificar la conexión API.',
        settings.DEFAULT_FROM_EMAIL,
        ['pepet2799@gmail.com'], # Enviamos al mismo correo para probar
        fail_silently=False,
    )
    print(f"✅ Resultado de send_mail: {result}")
    print("El correo fue aceptado por el backend.")
except Exception as e:
    print(f"❌ ERROR AL ENVIAR: {e}")
    if hasattr(e, 'response'):
        print(f"   Respuesta API: {e.response.content if hasattr(e.response, 'content') else 'N/A'}")

sys.stdout = original_stdout
log_file.close()

# Print confirmation to console
print("Diagnostico completado. Revisa email_diagnosis.log")
