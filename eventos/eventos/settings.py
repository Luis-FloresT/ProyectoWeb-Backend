import os
import environ
from pathlib import Path
  # Importante para la base de datos en la nube

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

# Database Configuration with Fast Failover
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'sandia'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', '123456'),
        'HOST': 'db', 
        'PORT': '5432',
        'CONN_MAX_AGE': 0,  # Don't persist connections to detect failures faster
        'OPTIONS': {
            'connect_timeout': 2,  # 2 second connection timeout
            'options': '-c statement_timeout=5000',  # 5 second query timeout
        },
    },
    'espejo': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'sandia_espejo',
        'USER': 'postgres',
        'PASSWORD': '123456',
        'HOST': 'db_espejo',
        'PORT': '5432',
        'CONN_MAX_AGE': 0,  # Don't persist connections
        'OPTIONS': {
            'connect_timeout': 2,  # 2 second connection timeout
            'options': '-c statement_timeout=5000',  # 5 second query timeout
        },
    }
}

# Database Routers
DATABASE_ROUTERS = ['eventos.router.ReplicationRouter']

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators
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