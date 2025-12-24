import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventos.settings')
django.setup()

from fiesta.models import ConfiguracionPago

def update_banks():
    print("--- Current Bank Configurations ---")
    bancos = ConfiguracionPago.objects.all()
    for b in bancos:
        print(f"ID: {b.id} | Banco: {b.banco_nombre} | Titular: {b.beneficiario} | Cuenta: {b.numero_cuenta}")

    # FIX: Remove/Update Paul Cruz
    target = bancos.filter(beneficiario__icontains="Paul Cruz").first()
    if target:
        print(f"\nFound target to update: {target.beneficiario}")
        target.banco_nombre = "Banco Pichincha"
        target.beneficiario = "Banco Pichincha" # Replacing personal name with Bank Name as requested?
        # User said: "quita la el nombre de paul cruz y pon banco pichincha"
        target.save()
        print("Updated successfully.")
    else:
        print("\nNo entry found for 'Paul Cruz'.")

if __name__ == "__main__":
    update_banks()
