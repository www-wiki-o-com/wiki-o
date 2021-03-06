r""" __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE.md file in the root directory of this source tree.
"""

from .settings_base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Host Config
ALLOWED_HOSTS = ['localhost', 'admin.localhost', '127.0.0.1']
INTERNAL_IPS = ['localhost']

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
    #    'allauth.socialaccount.providers.facebook',
    #    'allauth.socialaccount.providers.google',
    'invitations',

    # activity stream
    'notifications',
    'actstream',
    'hitcount',

    # subdomains
    'django_hosts',

    # toolbar
    'debug_toolbar',
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
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django_hosts.middleware.HostsResponseMiddleware',
]
