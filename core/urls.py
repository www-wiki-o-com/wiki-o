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
    path('contact', ContactView.as_view(), name='contact'),
    path('terms_and_conditions', TermsView.as_view(), name='terms'),
    path('privacy_policy', PoliciesView.as_view(), name='policy'),
    path('feedback', RedirectView.as_view(url='http://feedback.wiki-o.com'), name='feedback'),
]
