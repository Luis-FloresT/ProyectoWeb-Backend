# BURBUJITAS DE COLORES - Backend

API Django REST Framework para gestionar fiestas infantiles.

### Paso 1: Instalación
```bash
pip install -r requirements.txt
```
###  Descargar entorno que tendra la api 
```bash
- `pip install django-environ`
```

### Paso 2: Crear base de datos en PostgreSQL
Solo necesitas crear una base de datos vacía en PostgreSQL (ejemplo: `sandia`). 
**Eso es todo lo que debes hacer en PostgreSQL.**

### Paso 3: Acceder a la carpeta del proyecto
```bash
cd eventos
```

### Paso 4: Aplicar migraciones de base de datos
```bash
python manage.py makemigrations
```
```bash
python manage.py migrate
```

**IMPORTANTE**: El comando `migrate` crea TODAS las tablas automáticamente en la base de datos que creaste en el paso 2. No es necesario crear las tablas manualmente.

### Paso 5: Crear usuario administrador (opcional pero recomendado)
```bash
python manage.py createsuperuser
```

### Paso 6: Configuración de Variables (.env)

Crea un archivo .env en la raíz del proyecto (junto a manage.py) para configurar las credenciales de forma segura.
Contenido de ejemplo:

# --- SEGURIDAD ---
SECRET_KEY=!*
DEBUG=True

# --- BASE DE DATOS (PostgreSQL) ---
DB_NAME=sandia
DB_USER=postgres
DB_PASSWORD=tu_contraseña_aquí
DB_HOST=localhost
DB_PORT=5432

# --- CORREO (BREVO) ---
BREVO_API_KEY=tu_api_key_aquí


### Paso 7: Iniciar servidor
```bash
python manage.py runserver
```

El servidor estará disponible en http://127.0.0.1:8000

Panel de administración en http://127.0.0.1:8000/admin/

## Verificación de correo

- Al registrarse, se genera un token y se envía un correo de verificación al usuario.
- El enlace apunta a `http://127.0.0.1:8000/api/verificar-email/?token=<TOKEN>`.
- Al abrir el enlace, se activa el usuario (`is_active=True`) y se muestra una página de confirmación.

## Guía para compañeros (workflow)

- Crear rama de feature: `git checkout -b feature/email-verification-flow`
- Asegurarse de NO commitear claves: en `eventos/settings.py` debe estar `BREVO_API_KEY = os.getenv('BREVO_API_KEY', '')`
- Ejecutar:
	- `pip install -r requirements.txt`
	- `pip install django-environ`
	- `cd eventos`
	- `python manage.py migrate`
	- `python manage.py runserver`
- Probar registro y verificación:
	- POST a `/api/registro/`
	- Abrir el enlace enviado al correo
- Subir cambios:
	- `git add .`
	- `git commit -m "feat: flujo de verificación de correo con Brevo (anymail)"`
	- `git push -u origin feature/email-verification-flow`
	- Crear Pull Request a `main`

## Cómo funcionan los datos

- **Base de datos**: Se guardan automáticamente en PostgreSQL cuando el frontend envía datos a través de la API
- **Migraciones**: Todas las tablas (usuarios, servicios, combos, promociones, reservas, pagos, etc.) se crean automáticamente con el comando `migrate`
- **Panel Admin**: Puedes ver/editar todos los datos en http://127.0.0.1:8000/admin/ (requiere usuario creado en `createsuperuser`)
