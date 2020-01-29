# *******************************************************************************
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
# *******************************************************************************


''' Django notification urls file '''
# -*- coding: utf-8 -*-
from distutils.version import StrictVersion  # pylint: disable=no-name-in-module,import-error
from django import get_version
from notifications import views

if StrictVersion(get_version()) >= StrictVersion('2.0'):
    from django.urls import re_path as pattern
else:
    from django.conf.urls import url as pattern

urlpatterns = [
    pattern(r'^mark-all-as-read/$', views.mark_all_as_read,
            name='mark_all_as_read'),
    pattern(r'^mark-as-read/(?P<slug>\d+)/$',
            views.mark_as_read, name='mark_as_read'),
    pattern(r'^mark-as-unread/(?P<slug>\d+)/$',
            views.mark_as_unread, name='mark_as_unread'),
    pattern(r'^delete/(?P<slug>\d+)/$', views.delete, name='delete'),
]
app_name = 'notifications'
