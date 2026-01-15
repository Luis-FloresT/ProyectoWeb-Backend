import os
import environ
from pathlib import Path

# 1. DEFINIR BASE_DIR
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. INICIALIZAR ENVIRON
env = environ.Env()
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

# ALLOWED HOSTS TOTAL (Para Ngrok y Vercel)
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

# MIDDLEWARE: El orden de CorsMiddleware es vital
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'corsheaders.middleware.CorsMiddleware',  # <--- Siempre arriba de CommonMiddleware
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

# Database Configuration (Ajustada para estabilidad)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'sandia'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', '123456'),
        'HOST': os.environ.get('DB_HOST', 'db'), 
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,  # Mantener conexión activa para evitar "connection is closed"
        'OPTIONS': {
            'connect_timeout': 5,
            'options': '-c statement_timeout=10000',
        },
    },
    'espejo': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME_ESPEJO', 'sandia_espejo'),
        'USER': os.environ.get('DB_USER_ESPEJO', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD_ESPEJO', '123456'),
        'HOST': os.environ.get('DB_HOST_ESPEJO', 'db_espejo'),
        'PORT': os.environ.get('DB_PORT_ESPEJO', '5432'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'connect_timeout': 5,
            'options': '-c statement_timeout=10000',
        },
    }
}

DATABASE_ROUTERS = ['eventos.router.ReplicationRouter']

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- CONFIGURACIÓN DE CORS Y SEGURIDAD (LLAVE MAESTRA) ---

CORS_ALLOW_ALL_ORIGINS = True  # <--- Esto elimina cualquier error de CORS de raíz
CORS_ALLOW_CREDENTIALS = True

# AÑADE ESTAS DOS LÍNEAS AQUÍ:
APPEND_SLASH = True
ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = [
    "https://*.ngrok-free.dev",
    "https://*.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Indispensable para que Django acepte peticiones HTTPS desde el túnel
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    # Ajustes para producción (Vercel usa HTTPS por defecto)
    SECURE_SSL_REDIRECT = False  # Ngrok ya gestiona el SSL, poner en True puede causar bucles
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'