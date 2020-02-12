"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       wiki_o/models.py
@brief      A collection of app specific urls
@details    The `urlpatterns` list routes URLs to views. For more information please see:
                https://docs.djangoproject.com/en/2.1/topics/http/urls/
            Examples:
            Function views
                1. Add an import:  from my_app import views
                2. Add a URL to urlpatterns:  path('', views.home, name='home')
            Class-based views
                1. Add an import:  from other_app.views import Home
                2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
            Including another URLconf
                1. Import the include() function: from django.urls import include, path
                2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# Imports
# *******************************************************************************
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.conf.urls import url
from machina.app import board


# *******************************************************************************
# urls
# *******************************************************************************
urlpatterns = [
    path('', include('core.urls')),
    path('', include('theories.urls')),
    path('admin/', admin.site.urls),
    path('feedback/', include(board.urls)),
    path('', include('users.urls')),
    path('accounts/', include('allauth.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/actstream/', include('users.activity_urls', namespace='activity')),
    path('accounts/notifications/',
         include('users.notifications_urls', namespace='notifications')),
    path('accounts/invitations/',
         include('invitations.urls', namespace='invitations')),
]


# *******************************************************************************
# Django Toolbar
# *******************************************************************************
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
