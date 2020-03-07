"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE.md file in the root directory of this source tree.
"""

from django.shortcuts import render
from django.views import generic
from django.views.generic.base import RedirectView


# ************************************************************
#
# ************************************************************
class IndexView(RedirectView):
    url = 'alpha'


# ************************************************************
#
# ************************************************************
class AlphaView(generic.ListView):
    template_name = 'core/alpha.html'
    context_object_name = 'alpha'

    def get_queryset(self):
        """Return nothing."""
        return None


# ************************************************************
#
# ************************************************************


class HelpView(generic.ListView):
    template_name = 'core/help.html'
    context_object_name = 'help'

    def get_queryset(self):
        """Return nothing."""
        return None


# ************************************************************
#
# ************************************************************


class PolicyView(generic.ListView):
    template_name = 'core/policy01.html'
    context_object_name = 'policy'

    def get_queryset(self):
        """Return nothing."""
        return None


# ************************************************************
#
# ************************************************************


class TermsView(generic.ListView):
    template_name = 'core/terms01.html'
    context_object_name = 'terms'

    def get_queryset(self):
        """Return nothing."""
        return None


# ************************************************************
#
# ************************************************************


class AboutView(generic.ListView):
    template_name = 'core/about.html'
    context_object_name = 'about'

    def get_queryset(self):
        """Return nothing."""
        return None


# ************************************************************
#
# ************************************************************
def ContactView(request):

    # Setup
    user = request.user

    # Render
    context = {}
    return render(
        request,
        'core/contact.html',
        context,
    )
