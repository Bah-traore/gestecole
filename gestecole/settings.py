"""
Paramètres Django pour le projet gestecole.

Généré par 'django-admin startproject' en utilisant Django 5.1.6.

Pour plus d'informations sur ce fichier, voir
https://docs.djangoproject.com/en/5.1/topics/settings/

Pour la liste complète des paramètres et leurs valeurs, voir
https://docs.djangoproject.com/en/5.1/ref/settings/
"""
import os
import sys
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from dotenv import load_dotenv



# Construire les chemins dans le projet comme ceci: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Paramètres de démarrage rapide - non adaptés pour la production
# Voir https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

load_dotenv()
# AVERTISSEMENT DE SÉCURITÉ: gardez la clé secrète utilisée en production secrète!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-key-!tmp!') # 'django-insecure-zx5jum*sd6)0czg=aky##kyr21eh7i8@he&1x#&xq_yy552#3v'

ALLOWED_HOSTS = ['*']

CORS_ALLOWED_ORIGINS = [
    'https://ac55-2001-42c0-82cf-b600-cba5-fa5a-eea3-4745.ngrok-free.app',
    "http://localhost:59374",
    "http://localhost:8000",
    "http://192.168.1.11:8000",
    "http://10.0.2.2:8000",
    'http://127.0.0.1:8000',
]


# AVERTISSEMENT DE SÉCURITÉ: ne pas exécuter avec le débogage activé en production!

#
CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Ou l'URL de votre broker
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Paris'
CELERY_BEAT_SCHEDULE = {
    'update-exam-status': {
        'task': 'APP_G2S.tasks.update_exam_status',
        'schedule': crontab(hour=0, minute=5),  # Tous les jours à 00:05
    },
    'verification-impayes': {
            'task': 'APP_G2S.tasks.verifier_impayes',
            'schedule': crontab(hour=8, minute=0),  # Tous les jours à 8h
        },
}


SMS_PROVIDER = 'ORANGE'  # ou 'MALITEL'
SMS_SENDER_ID = 'ECOLEXYZ'  # ID approuvé par l'opérateur
ORANGE_API_KEY = 'votre_cle_api_orange'
MALITEL_API_KEY = 'votre_cle_api_malitel'
ORANGE_SMS_URL = 'https://api.orange.com/smsmessaging/v1/outbound'
MALITEL_SMS_URL = 'https://api.malitel.ml/sms/v1/send'
ECOLE_NOM = "VOTRE ECOLE"  # Pour l'identifiant des SMS

# Configuration SMS
SMS_REMINDER_DAYS = [7, 3, 1]  # Jours avant échéance pour rappel





DEBUG = True
METHODE_POST = "POST"


SMS_CODE_VALIDITY = 15  # minutes
LOGIN_ATTEMPTS_TIMEOUT = 15 # minutes aussi
SESSION_COOKIE_AGE = 3600 # seconde, 1 Heure
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_NAME = 'sessionid'
SECURE_BROWSER_XSS_FILTER = True
CSRF_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SAMESITE = 'Strict'
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

ALLOWED_HOSTS = [

'*',
    '.ngrok-free.app'

]

CORS_ALLOWED_ORIGINS = [
    'https://4ea9-2001-42c0-8246-a300-6ba2-9bb1-cce0-5682.ngrok-free.app',
    'http://localhost:59374',
    'http://localhost:8000',
    'http://192.168.1.11:8000',
    'http://10.0.2.2:8000',
    'http://127.0.0.1:8000'
]


# Définition des applications
AUTH_USER_MODEL = 'core_admin.SuperAdmin' # 'auth.User' # 'APP_G2S.Administrateur'


AUTHENTICATION_BACKENDS = [
    'APP_G2S.auth_backends.RolePermissionBackend',
    'django.contrib.auth.backends.ModelBackend',
    'APP_G2S.auth_backends.TelephoneBackend',
    'APP_G2S.auth_backends.AdminBackend',
]

PHONENUMBER_DEFAULT_REGION = "ML"
PHONENUMBER_DB_FORMAT = "NATIONAL"

# Configuration CRISPY
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# Configuration MEDIA
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
TWO_FACTOR_ENABLED = True


PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'core_admin',
    'APP_G2S',
    'phonenumber_field',
    'crispy_forms',
    'crispy_bootstrap5',
    'rest_framework',
    'corsheaders',
    'rest_framework_simplejwt',
    'widget_tweaks',

]

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),  # Durée de validité du token
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,  # Utilise la clé secrète de Django
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'identifiant',
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'APP_G2S.middleware.TenantMiddleware',
    'APP_G2S.middleware.HierarchyMiddleware',
    'APP_G2S.middleware.PerformanceMiddleware',
]

# Configuration multi-tenant
TENANT_REQUIRED = False  # Si True, une école (tenant) est requise pour accéder à l'application
MAIN_DOMAIN = 'http://127.0.0.1:8000/superadmin/login'  # Domaine principal pour l'administration multi-tenant

ROOT_URLCONF = 'gestecole.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'APP_G2S.context_processors.user_permissions',
                'APP_G2S.context_processors.tenant_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'gestecole.wsgi.application'


# Base de données
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'gestecole',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    },

}



# Validation des mots de passe
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Internationalisation
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Fichiers statiques (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

# Type de champ de clé primaire par défaut
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(PROJECT_ROOT, 'utils'))
