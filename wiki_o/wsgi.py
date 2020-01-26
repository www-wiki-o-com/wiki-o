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
Exposes the WSGI callable as a module-level variable named ``application``. 
For more information on this file, see 
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/ 
""" 
import os 
import time 
import traceback 
import signal 
import sys
 
from django.core.wsgi import get_wsgi_application 

# adjust the Python version in the line below as needed 
sys.path.append('/home/wiki-o/code/django')
sys.path.append('/home/wiki-o/code/venv/lib/python3.5/site-packages')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wiki_o.settings')

try: 
    application = get_wsgi_application() 
except Exception: 
    # Error loading applications 
    if 'mod_wsgi' in sys.modules: 
        traceback.print_exc() 
        os.kill(os.getpid(), signal.SIGINT) 
        time.sleep(2.5)
