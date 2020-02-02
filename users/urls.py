"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       users/urls.py
@brief      A collection of app specific urls
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""

# *******************************************************************************
# imports
# *******************************************************************************
from django.conf.urls import url
from django.urls import include, path
from users.views import *
from notifications.views import mark_as_read


# *******************************************************************************
# urls
# *******************************************************************************
app_name = 'users'
urlpatterns = [
    path('accounts/profile/', PrivateProfileView, name='profile-edit'),
    path('accounts/<int:pk>/', PublicProfileView, name='profile-detail'),
    path('accounts/notifications/', NotificationsView, name='notifications'),

    path('violations/', ViolationIndexView, name='violations'),
    path('violation/<int:pk>/resolve/', ViolationResolveView,
         name='violation-resolve'),
]
