import os
import environ
from pathlib import Path
import dj_database_url  # Importante para la base de datos en la nube

# 1. DEFINIR BASE_DIR
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. INICIALIZAR ENVIRON
env = environ.Env()
# Leer el archivo .env ubicado UN NIVEL arriba de BASE_DIR
env_path = os.path.join(BASE_DIR.parent, '.env')
environ.Env.read_env(env_path)

# 3. AJUSTES DE SEGURIDAD
SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)

# 4. CONFIGURACIÓN DE BREVO (ANYMAIL)
BREVO_API_KEY = env('BREVO_API_KEY')

EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
ANYMAIL = {
    "BREVO_API_KEY": BREVO_API_KEY,
}

# 5. CONFIGURACIÓN DEL REMITENTE
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
SERVER_EMAIL = env('SERVER_EMAIL')

# Permitir todos los hosts para evitar errores en Render
ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders', 
    'rest_framework',
    'fiesta',
    'rest_framework.authtoken',
    'anymail',  
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# MIDDLEWARE CORREGIDO (Orden correcto y sin duplicados)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",  # <--- Vital para Render
    'corsheaders.middleware.CorsMiddleware',       # <--- Antes de respuestas comunes
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'eventos.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'fiesta' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'eventos.wsgi.application'

# Database
# Configuración inteligente: usa la URL de Render si existe, si no usa tu local
DATABASES = {
    'default': dj_database_url.config(
        # Cambia '260917' por tu contraseña real si es diferente
        default=f"postgres://postgres:260917@localhost:5432/sandia",
        conn_max_age=600
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static and Media files
STATIC_URL = 'static/'
# Carpeta donde se recolectarán los estáticos en producción
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS
CORS_ALLOW_ALL_ORIGINS = True

# Almacenamiento optimizado de estáticos para producción (WhiteNoise)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'