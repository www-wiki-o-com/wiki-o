r""" __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE.md file in the root directory of this source tree.
"""

from django.conf import settings
from django_hosts import patterns, host
host_patterns = patterns(
    '',
    host(r'www', 'wiki_o.urls', name='www'),
    host(r'admin', 'wiki_o.admin_urls', name='admin'),
)
