# BURBUJITAS DE COLORES - Backend

API Django REST Framework para gestionar fiestas infantiles.

## Instalación

### Paso 1: Descargar dependencias
```bash
pip install -r requirements.txt
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
python manage.py migrate
```

**IMPORTANTE**: El comando `migrate` crea TODAS las tablas automáticamente en la base de datos que creaste en el paso 2. No es necesario crear las tablas manualmente.

### Paso 5: Crear usuario administrador (opcional pero recomendado)
```bash
python manage.py createsuperuser
```

<<<<<<< HEAD
### Paso 6: Configurar correo (Brevo)

Para que el envío de correos funcione, debes configurar la API Key de Brevo como variable de entorno.

Windows (PowerShell):
```powershell
$env:BREVO_API_KEY = "TU_API_KEY_DE_BREVO"
```

Linux/Mac (bash):
```bash
export BREVO_API_KEY="TU_API_KEY_DE_BREVO"
```

Si no configuras `BREVO_API_KEY`, el backend usa el backend de consola y verás el contenido del correo en la terminal (modo desarrollo).

### Paso 7: Iniciar servidor
=======
### Paso 6: Iniciar servidor
>>>>>>> main
```bash
python manage.py runserver
```

El servidor estará disponible en http://127.0.0.1:8000

Panel de administración en http://127.0.0.1:8000/admin/

<<<<<<< HEAD
## Verificación de correo

- Al registrarse, se genera un token y se envía un correo de verificación al usuario.
- El enlace apunta a `http://127.0.0.1:8000/api/verificar-email/?token=<TOKEN>`.
- Al abrir el enlace, se activa el usuario (`is_active=True`) y se muestra una página de confirmación.

## Guía para compañeros (workflow)

- Crear rama de feature: `git checkout -b feature/email-verification-flow`
- Asegurarse de NO commitear claves: en `eventos/settings.py` debe estar `BREVO_API_KEY = os.getenv('BREVO_API_KEY', '')`
- Ejecutar:
	- `pip install -r requirements.txt`
	- `pip install django-anymail`
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

=======
>>>>>>> main
## Cómo funcionan los datos

- **Base de datos**: Se guardan automáticamente en PostgreSQL cuando el frontend envía datos a través de la API
- **Migraciones**: Todas las tablas (usuarios, servicios, combos, promociones, reservas, pagos, etc.) se crean automáticamente con el comando `migrate`
- **Panel Admin**: Puedes ver/editar todos los datos en http://127.0.0.1:8000/admin/ (requiere usuario creado en `createsuperuser`)
