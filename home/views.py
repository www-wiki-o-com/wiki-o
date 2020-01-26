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


from django.shortcuts import render
from django.views import generic
from django.views.generic.base import RedirectView


#************************************************************
# 
#************************************************************
class IndexView(RedirectView):
    url = 'alpha'


#************************************************************
# 
#************************************************************
class AlphaView(generic.ListView):
    template_name = 'home/alpha.html'
    context_object_name = 'alpha'

    def get_queryset(self):
        """Return nothing."""
        return None

#************************************************************
# 
#************************************************************
class HelpView(generic.ListView):
    template_name = 'home/help.html'
    context_object_name = 'help'

    def get_queryset(self):
        """Return nothing."""
        return None

#************************************************************
# 
#************************************************************
class PolicyView(generic.ListView):
    template_name = 'home/policy01.html'
    context_object_name = 'policy'

    def get_queryset(self):
        """Return nothing."""
        return None

#************************************************************
# 
#************************************************************
class TermsView(generic.ListView):
    template_name = 'home/terms01.html'
    context_object_name = 'terms'

    def get_queryset(self):
        """Return nothing."""
        return None

#************************************************************
# 
#************************************************************
class AboutView(generic.ListView):
    template_name = 'home/about.html'
    context_object_name = 'about'

    def get_queryset(self):
        """Return nothing."""
        return None


#************************************************************
# 
#************************************************************
def ContactView(request):
    
    # Setup
    user = request.user

    # RENDER
    context = {
    }
    return render(
              request,
              'home/contact.html',
              context,
           )


