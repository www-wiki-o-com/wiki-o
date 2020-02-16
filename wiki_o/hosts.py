"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       wiki-o/hosts.py
@brief      The private server file for Django
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""

from django.conf import settings
from django_hosts import patterns, host
host_patterns = patterns(
    '',
    host(r'www', 'wiki_o.urls', name='www'),
    host(r'admin', 'wiki_o.admin_urls', name='admin'),
)
