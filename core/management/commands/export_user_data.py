"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       core/management/command/export_user_data.py
@copyright  GNU Public License, 2018
@authors    Frank Imeson
@brief      A managment script for exporting user data from the database
"""

# *******************************************************************************
# Imports
# *******************************************************************************
from django.core.management.base import BaseCommand
from django.core import serializers

from users.models import User

# *******************************************************************************
# Defines
# *******************************************************************************

# *******************************************************************************
# Methods
# *******************************************************************************


class Command(BaseCommand):
    """Export user data."""
    help = __doc__

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('archive_path', nargs='?', type=str)

        # Named (optional) arguments
        parser.add_argument(
            '--fields',
            nargs='+',
            help='Choose the fields .',
        )

    def handle(self, *args, **options):
        """The method that is run when the commandline is invoked."""

        if options['fields']:
            data = serializers.serialize('json', User.objects.all(), fields=options['fields'])
        else:
            data = serializers.serialize('json', User.objects.all())

        if options['archive_path']:
            with open(options['archive_path'], 'w') as f:
                f.write(data)
        else:
            print(data)
