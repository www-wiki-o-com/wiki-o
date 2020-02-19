"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       wiki-o/wsgi.py
@brief      Exposes the WSGI callable as a module-level variable named application.
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""

import os
import time
import traceback
import signal
import sys

from django.core.wsgi import get_wsgi_application

# Convert Apache environement varaibles to os environement variables.
def application_wrapper(wsgi_environ, start_response):
    """A wrapper that loads environment varaibles passed in by Apache."""
    apache_env_vars = ['DJANGO_SETTINGS_MODULE']
    for key in apache_env_vars:
        try:
            os.environ[key] = wsgi_environ[key]
        except KeyError:
            # The WSGI environment doesn't have the key
            pass
    application_ = get_wsgi_application()
    return application_(wsgi_environ, start_response)

# Setup
sys.path.append('/home/django/www.wiki-o.com')
sys.path.append('/home/django/venv/lib/python3.6/site-packages')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wiki_o.settings_local')

try:
    application = application_wrapper
except Exception:
    # Error loading applications
    if 'mod_wsgi' in sys.modules:
        traceback.print_exc()
        os.kill(os.getpid(), signal.SIGINT)
        time.sleep(2.5)
