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
from django.urls import path
from home.views import *

app_name = 'home'
urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('alpha', AlphaView.as_view(), name='alpha'),
    path('about', AboutView.as_view(), name='about'),
    path('help', HelpView.as_view(), name='help'),
    path('contact', ContactView, name='contact'),
    path('terms_and_conditions', TermsView.as_view(), name='terms'),
    path('privacy_policy', PolicyView.as_view(), name='policy'),
]
