from app.settings import *

DEBUG = True

USE_FORWARDER = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_sorcery',
    'rest_framework',
    'drf_yasg',
    'corsheaders',
    'vox_message',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'ALCHEMY_OPTIONS': {
            'engine_options': {
                'connect_args': {'timeout': 10000}
            }
        }
    }
}

SQLALCHEMY_CONNECTIONS = DATABASES

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'sqlalchemy': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
        'kafka': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
    },
}

STATIC_URL = 'static/'
STATIC_ROOT = 'static/'
