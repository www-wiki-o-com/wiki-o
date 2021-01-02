r""" __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE.md file in the root directory of this source tree.
"""

# *******************************************************************************
# Imports
# *******************************************************************************
from distutils.version import StrictVersion  # pylint: disable=no-name-in-module,import-error

from notifications import views
from django import get_version
if StrictVersion(get_version()) >= StrictVersion('2.0'):
    from django.urls import re_path as pattern
else:
    from django.conf.urls import url as pattern

# *******************************************************************************
# urls
# *******************************************************************************
urlpatterns = [
    pattern(r'^mark-all-as-read/$', views.mark_all_as_read, name='mark_all_as_read'),
    pattern(r'^mark-as-read/(?P<slug>\d+)/$', views.mark_as_read, name='mark_as_read'),
    pattern(r'^mark-as-unread/(?P<slug>\d+)/$', views.mark_as_unread, name='mark_as_unread'),
    pattern(r'^delete/(?P<slug>\d+)/$', views.delete, name='delete'),
]
app_name = 'notifications'
