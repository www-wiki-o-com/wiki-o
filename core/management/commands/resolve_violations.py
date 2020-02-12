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
# Imports
# *******************************************************************************
from django.core.management.base import BaseCommand
from users.models import Violation


# *******************************************************************************
# Defines
# *******************************************************************************


# *******************************************************************************
# Methods
# *******************************************************************************


class Command(BaseCommand):
    """Tallies and closes open polls for violations."""
    help = __doc__

    def handle(self, *args, **options):
        """The method that is run when the commandline is invoked."""
        for violation in Violation.get_violations(opened=True, closed=False):
            if violation.poll_is_done():
                violation.close_poll()
