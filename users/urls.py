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
# Imports
# *******************************************************************************
from django.urls import path
from users.views import private_profile_view, public_profile_view, notifications_view
from users.views import violation_index_view, violation_resolve_view


# *******************************************************************************
# urls
# *******************************************************************************
app_name = 'users'
urlpatterns = [
    path('accounts/profile/', private_profile_view, name='profile-edit'),
    path('accounts/<int:pk>/', public_profile_view, name='profile-detail'),
    path('accounts/notifications/', notifications_view, name='notifications'),
    path('violations/', violation_index_view, name='violations'),
    path('violation/<int:pk>/resolve/', violation_resolve_view, name='violation-resolve'),
]
