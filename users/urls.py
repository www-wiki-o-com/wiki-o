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


from django.conf.urls import url
from django.urls import include, path
from users.views import *
from notifications.views import mark_as_read

app_name = 'users'
urlpatterns = [
    path('accounts/profile/', PrivateProfileView, name='profile-edit'),
    path('accounts/<int:pk>/', PublicProfileView, name='profile-detail'),
    path('accounts/notifications/', NotificationsView, name='notifications'),

    path('violations/', ViolationIndexView, name='violations'),
    path('violation/<int:pk>/resolve/', ViolationResolveView,
         name='violation-resolve'),
]
