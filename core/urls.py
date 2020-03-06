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
from django.conf.urls import url
from django.urls import path
from core.views import *

# *******************************************************************************
# urls
# *******************************************************************************
app_name = 'core'
urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('alpha', AlphaView.as_view(), name='alpha'),
    path('about', AboutView.as_view(), name='about'),
    path('help', HelpView.as_view(), name='help'),
    path('contact', ContactView, name='contact'),
    path('terms_and_conditions', TermsView.as_view(), name='terms'),
    path('privacy_policy', PolicyView.as_view(), name='policy'),
]
