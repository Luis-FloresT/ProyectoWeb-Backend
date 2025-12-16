import requests
import uuid
import random
import os
import django

# Setup Django to access DB
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventos.settings')
django.setup()
from eventos.fiesta.models import EmailVerificationToken

def register_and_test_verification():
    # 1. Register User
    url_reg = "http://127.0.0.1:8000/api/registro/"
    headers = {"Content-Type": "application/json"}
    
    random_id = str(uuid.uuid4())[:8]
    email = f"festive_{random_id}@example.com"
    data = {
        "nombre": f"FiestaUser_{random_id}",
        "apellido": "Party",
        "email": email,
        "clave": "password123",
        "telefono": f"555-{random.randint(1000,9999)}"
    }
    
    print(f"1. Registering: {email}...")
    try:
        resp = requests.post(url_reg, json=data, headers=headers)
        if resp.status_code == 200 or resp.status_code == 201:
            print("   Registration Successful (Email sent).")
        else:
            print(f"   Registration Failed: {resp.status_code} {resp.text}")
            return
            
        # 2. Find Token in DB
        print("2. Retrieving Token from DB...")
        token_obj = EmailVerificationToken.objects.filter(user__email=email).last()
        if not token_obj:
            print("   Token not found!")
            return
        token = token_obj.token
        print(f"   Token found: {token}")
        
        # 3. Test Verification Page
        url_verify = f"http://127.0.0.1:8000/api/verificar-email/?token={token}"
        print(f"3. Accessing Verification URL: {url_verify} ...")
        resp_verify = requests.get(url_verify)
        
        if resp_verify.status_code == 200:
            print("   Verification Request Successful.")
            if "¡Verificación Exitosa!" in resp_verify.text:
                print("   SUCCESS: Validated Success Page HTML content.")
            else:
                print("   WARNING: Success Page HTML content verification failed.")
                print(resp_verify.text[:200])
        else:
            print(f"   Verification Failed: {resp_verify.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    register_and_test_verification()
