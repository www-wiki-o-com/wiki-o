"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       core/management/resolve_violations.py
@brief      A debug script for updating the database
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
from users.models import Violation


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
    help = 'Tallies and closes open polls for violations.'

    # ******************************
    #
    # ******************************
    def handle(self, *args, **options):
        for violation in Violation.get_violations(opened=True, closed=False):
            if violation.poll_is_done():
                violation.close_poll()
