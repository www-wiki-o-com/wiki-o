"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE file in the root directory of this source tree.
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
