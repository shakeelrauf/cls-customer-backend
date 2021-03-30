"""
Django settings for calgary_web_portal project.

Generated by 'django-admin startproject' using Django 3.0.10.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os
import sys
from decouple import config

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool, default=True)

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '10.100.67.52', '2b36a310257c.ngrok.io', 'customerportal.calgarylockandsafe.com']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third parties apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'djcelery_email',

    # Custom apps
    'customer_dashboard',
    'key_door_finder',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # core headers
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware'
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 10
}

ROOT_URLCONF = 'calgary_web_portal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'calgary_web_portal.wsgi.application'

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases


DATABASES = {
    'default': {
        'ENGINE': config('CUSDB_ENGINE'),
        'NAME': config('CUSDB_NAME'),
        'HOST': config('CUSDB_HOST'),
        'USER': config('CUSDB_USER'),
        'PASSWORD': config('CUSDB_PASSWORD'),
        'OPTIONS': {
            'driver': config('CUSDB_DRIVER'),
            'unicode_results': config('CUSDB_UNICODE_RESULTS', cast=bool),
        }
    },
    'esc': {
        'ENGINE': config('ESC_ENGINE'),
        'NAME': config('ESC_NAME'),
        'HOST': r'CLS-SQL1\ESC',
        'USER': config('ESC_USER'),
        'PASSWORD': config('ESC_PASSWORD'),
        'OPTIONS': {
            'extra_params': config('ESC_EXTRA_PARAMS'),
            'driver': config('ESC_DRIVER'),
            'unicode_results': config('ESC_UNICODE_RESULTS', cast=bool),
            'host_is_server': config('ESC_HOST_IS_SERVER'),
            'ESC_SQLSRV_ATTR_QUERY_TIMEOUT': config('ESC_SQLSRV_ATTR_QUERY_TIMEOUT', cast=int)
        }
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/django_static/'
STATICFILES_DIRS = [
    STATIC_DIR
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

AUTH_USER_MODEL = 'customer_dashboard.User'


# SMTP mail configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

EMAIL_FOR_CREATE_NEW_PRIMARY_USER = 'Lars@calgarylockandsafe.com'
EMAIL_TO_CALGARY = 'AR@calgarylockandsafe.com'
EMAIL_TO_CALGARY_REPORTS = config('EMAIL_TO_CALGARY_REPORTS')
EMAIL_FOR_SERVICE_REQUEST = 'ap@calgarylockandsafe.com'


# cors settings
CORS_ALLOW_ALL_ORIGINS = True


# set domain name for sending url to user for resetting password
DOMAIN_NAME = 'http://10.100.67.52'
LOGO = f"{DOMAIN_NAME}:8000/static/images/logo.png"

# set time(in secs) for token expiration
PASSWORD_RESET_TOKEN_TIMEOUT = 600


# Celery Configuration Options
BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'


# braintree configuration
if len(sys.argv) >= 2 and sys.argv[1] == 'runserver':
    BRAINTREE_PRODUCTION = False
else:
    BRAINTREE_PRODUCTION = True
BRAINTREE_MERCHANT_ID = config('BRAINTREE_MERCHANT_ID')
BRAINTREE_PUBLIC_KEY = config('BRAINTREE_PUBLIC_KEY')
BRAINTREE_PRIVATE_KEY = config('BRAINTREE_PRIVATE_KEY')


# logger setting
LOGGING = {
    'version': 1,
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG'
        }
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'calgary.log'),
            'formatter': 'simple'
        }
    },
    'formatters': {
        'simple': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        }
    }
}
