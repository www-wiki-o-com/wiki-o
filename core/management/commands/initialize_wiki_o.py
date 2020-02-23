"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       core/management/hack.py
@brief      A database managment script for initializing the database
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# Imports
# *******************************************************************************
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from users.maintence import create_groups_and_permissions
from theories.utils import create_categories


# *******************************************************************************
# Defines
# *******************************************************************************


# *******************************************************************************
# Methods
# *******************************************************************************


class Command(BaseCommand):
    """Updates permissions, categories, and site."""
    help = __doc__

    def handle(self, *args, **options):
        """The method that is run when the commandline is invoked."""
        create_groups_and_permissions()
        create_categories()
        site = Site.objects.first()
        site.domain = 'wiki-o.com'
        site.name = 'Wiki-O'
        site.save()
