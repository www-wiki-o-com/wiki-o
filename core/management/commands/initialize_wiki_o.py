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
# imports
# *******************************************************************************
import logging
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from users.utils import create_groups_and_permissions
from theories.utils import create_categories, create_reserved_nodes


# *******************************************************************************
# defines
# *******************************************************************************


# *******************************************************************************
# methods
# *******************************************************************************


# ************************************************************
#
# ************************************************************
class Command(BaseCommand):
    help = 'Updates permissions, categories, and site.'

    # ******************************
    #
    # ******************************
    def handle(self, *args, **options):
        create_groups_and_permissions()
        create_categories()
        site = Site.objects.first()
        site.domain = 'wiki-o.com'
        site.name = 'Wiki-O'
        site.save()
