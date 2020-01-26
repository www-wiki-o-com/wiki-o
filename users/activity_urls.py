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


try:
    from django.urls import url
except ImportError:
    from django.conf.urls import url

from actstream import feeds, views


urlpatterns = [
    # Follow/Unfollow API
    url(
        r'^follow/(?P<content_type_id>[^/]+)/(?P<object_id>[^/]+)/(?:(?P<flag>[^/]+)/)?$',
        views.follow_unfollow,
        name='follow'
    ),
    url(
        r'^follow_all/(?P<content_type_id>[^/]+)/(?P<object_id>[^/]+)/(?:(?P<flag>[^/]+)/)?$',
        views.follow_unfollow,
        {'actor_only': False},
        name='follow_all'
    ),
    url(
        r'^unfollow_all/(?P<content_type_id>[^/]+)/(?P<object_id>[^/]+)/(?:(?P<flag>[^/]+)/)?$',
        views.follow_unfollow,
        {'actor_only': False, 'do_follow': False},
        name='unfollow_all'
    ),
    url(
        r'^unfollow/(?P<content_type_id>[^/]+)/(?P<object_id>[^/]+)/(?:(?P<flag>[^/]+)/)?$',
        views.follow_unfollow,
        {'do_follow': False},
        name='unfollow'
    ),
]
app_name = 'actstream'
