"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE.md file in the root directory of this source tree.
"""

import os
import sys

# Import project environment variables ('PGUSER', 'PGPASSWORD', 'SECRET_KEY', ...)
try:
    import wiki_o.env_vars
except ImportError:
    import wiki_o.example_env_vars

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',

    # helpers
    'reversion',
    'url_tools',
    'django_nose',
    'crispy_forms',
    'rules.apps.AutodiscoverRulesConfig',

    # wiki-o
    'theories',
    'core',

    # user authentication
    'users',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'invitations',

    # activity stream
    'notifications',
    'actstream',
    'hitcount',

    # subdomains
    'django_hosts',
]

MIDDLEWARE = [
    'django_hosts.middleware.HostsRequestMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_hosts.middleware.HostsResponseMiddleware',
]

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
                'django.template.context_processors.request',
            ],
        },
    },
]
TEMPLATE_CONTEXT_PROCESSORS = ('url_tools.context_processors.current_url',)
CRISPY_TEMPLATE_PACK = 'bootstrap4'

AUTHENTICATION_BACKENDS = [
    'rules.permissions.ObjectPermissionBackend',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
AUTH_USER_MODEL = 'users.User'
SITE_ID = 1  # used by allauth and activity stream

DEFAULT_HOST = 'www'
ROOT_URLCONF = 'wiki_o.urls'
ROOT_HOSTCONF = 'wiki_o.hosts'
WSGI_APPLICATION = 'wiki_o.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'wiki_o',
        'USER': os.environ['PGUSER'],
        'PASSWORD': os.environ['PGPASSWORD'],
        'HOST': 'localhost',
        'PORT': '',
    }
}

# Password Validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators
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
ACCOUNT_ADAPTER = 'invitations.models.InvitationsAdapter'

STATICFILES_DIRS = ()

CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',}}

# Search Engine
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
    },
}

# Activity Stream Config
ACTSTREAM_SETTINGS = {}

# AllAuth Config
ACCOUNT_USERNAME_MIN_LENGTH = 3
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_CONFIRM_EMAIL_ON_GET = False
ACCOUNT_EMAIL_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False

# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

# Fixtures
PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIRS = (os.path.join(PROJECT_ROOT, 'fixtures'),)

# Unit Test Environment
if 'test' in sys.argv:
    PASSWORD_HASHERS = ('django.contrib.auth.hashers.MD5PasswordHasher',)
    # DATABASES = {
    #     'default': {
    #         'ENGINE': 'django.db.backends.postgresql',
    #         # 'ENGINE': 'django.db.backends.sqlite3',
    #         'NAME': 'test_database',
    #         'TEST_NAME': 'test_database',
    #     }
    # }
    DEBUG = False
    TEMPLATE_DEBUG = False

# Use nose to run all tests
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# Tell nose to measure coverage on the 'foo' and 'bar' apps
#NOSE_ARGS = [
#    '--with-coverage',
#    '--cover-package=core,theories,users',
#]
