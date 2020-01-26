#*******************************************************************************
# Wiki-O: A web service for sharing opinions and avoiding arguments.
# Copyright (C) 2018 Frank Imeson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#*******************************************************************************

"""
Django settings for wiki_o project.

Generated by 'django-admin startproject' using Django 2.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
import sys
from machina import MACHINA_MAIN_TEMPLATE_DIR
from machina import MACHINA_MAIN_STATIC_DIR
from machina import get_apps as get_machina_apps


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '123'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1']
INTERNAL_IPS = ['127.0.0.1']


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
    'dbbackup',
    'annoying',
    'reversion',
    'url_tools',
    'crispy_forms',
    'rules.apps.AutodiscoverRulesConfig',

    # wiki-o
    'theories',
    'home',

    # user authentication
    'users',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
#    'allauth.socialaccount.providers.facebook',
#    'allauth.socialaccount.providers.google',
    'invitations',

    # forum
    'mptt',
    'haystack',
    'widget_tweaks',
    
    # activity stream
    'notifications',
    'actstream',
    'hitcount',
    
    # toolbar
    'debug_toolbar',
] + get_machina_apps()

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'machina.apps.forum_permission.middleware.ForumPermissionMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
          os.path.join(BASE_DIR, 'forum/templates'),
          MACHINA_MAIN_TEMPLATE_DIR,
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
                'machina.core.context_processors.metadata',
            ],
#            'loaders': [
#                ('django.template.loaders.cached.Loader', [
#                    'django.template.loaders.filesystem.Loader',
#                    'django.template.loaders.app_directories.Loader',
#                    'amp_tools.loader.Loader',
#                ]),
#            ],
        },
    },
]
TEMPLATE_CONTEXT_PROCESSORS = (
    'url_tools.context_processors.current_url',
)
CRISPY_TEMPLATE_PACK = 'bootstrap4'

AUTHENTICATION_BACKENDS = [
    'rules.permissions.ObjectPermissionBackend',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
AUTH_USER_MODEL   = 'users.User'
SITE_ID           = 1 # used by allauth and activity stream

ROOT_URLCONF      = 'wiki_o.urls'
WSGI_APPLICATION  = 'wiki_o.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases
DATABASES = {
  'default': {
    'ENGINE':   'django.db.backends.postgresql',
    'NAME':     'wiki_o',
    'USER':     'django',
    'PASSWORD': 'password',
    'HOST':     'localhost',
    'PORT':     '',
  }
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]
ACCOUNT_ADAPTER = 'invitations.models.InvitationsAdapter'

STATICFILES_DIRS = (
    MACHINA_MAIN_STATIC_DIR,
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'machina_attachments': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp',
    },
}


# Search Engine
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
    },
}


# Machina_Forum Config
MACHINA_FORUM_NAME = 'feedback'
MACHINA_PROFILE_AVATARS_ENABLED = False
MACHINA_DEFAULT_AUTHENTICATED_USER_FORUM_PERMISSIONS = [
    'can_see_forum',
    'can_read_forum',
    'can_edit_own_posts',
    'can_post_without_approval',
    'can_create_polls',
    'can_vote_in_polls',
    'can_download_file',
]

# Activity Stream Config
ACTSTREAM_SETTINGS = {
}


# AllAuth Config
ACCOUNT_USERNAME_MIN_LENGTH             = 3
ACCOUNT_AUTHENTICATION_METHOD           = "username_email"
ACCOUNT_CONFIRM_EMAIL_ON_GET            = False
ACCOUNT_EMAIL_REQUIRED                  = False
ACCOUNT_EMAIL_VERIFICATION              = "none"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION     = False


# Email setup (postfix)
EMAIL_BACKEND         = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST            = 'localhost'
EMAIL_PORT            = 25
EMAIL_HOST_USER       = ''
EMAIL_HOST_PASSWORD   = ''
DEFAULT_FROM_EMAIL    = 'accounts@wiki-o.com'
EMAIL_USE_TLS         = False


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/
LANGUAGE_CODE   = 'en-us'
TIME_ZONE       = 'UTC'
USE_I18N        = True
USE_L10N        = True
USE_TZ          = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/
STATIC_URL    = '/static/'
STATIC_ROOT   = os.path.join(BASE_DIR, 'static/')

PROJECT_ROOT  = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIRS  = (os.path.join(PROJECT_ROOT, 'fixtures'),)

# backup config
DBBACKUP_STORAGE         = 'django.core.files.storage.FileSystemStorage'
DBBACKUP_STORAGE_OPTIONS = {'location': '/home/wiki-o/backups'}

DBBACKUP_CONNECTORS = {
    'default': {
        'USER':     'user',
        'PASSWORD': 'password',
    }
}

# Logging config
#LOGGING = {
#    'version': 1,
#    'disable_existing_loggers': False,
#    'handlers': {
#        'file': {
#            'level':      'ERROR',
#            'class':      'logging.FileHandler',
#            'filename':   os.path.join(BASE_DIR, 'logs/errors.log'),
#        },
#    },
#    'loggers': {
#        'django': {
#            'handlers':   ['file'],
#            'level':      'ERROR',
#            'propagate':  True,
#        },
#    },
#}

# Special setup for testing
# Ran 90 tests in 41.304s -> Ran 90 tests in 17.146s
if 'test' in sys.argv:
    PASSWORD_HASHERS = (
      'django.contrib.auth.hashers.MD5PasswordHasher',
    )
    DATABASES = {
      'default': {
        'ENGINE':     'django.db.backends.sqlite3',
        'NAME':       'test_database',            
        'TEST_NAME':  'test_database',            
      }
    }
    DEBUG = False
    TEMPLATE_DEBUG = False



