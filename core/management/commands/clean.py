"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       core/management/command/clean.py
@copyright  GNU Public License, 2018
@authors    Frank Imeson
@brief      A managment script for cleaning up the database
"""


# *******************************************************************************
# Imports
# *******************************************************************************
import os
import re
import glob
import datetime
import psycopg2

from django.core.management.base import BaseCommand
from theories.models import Category


# *******************************************************************************
# Defines
# *******************************************************************************


# *******************************************************************************
# Methods
# *******************************************************************************


class Command(BaseCommand):
    """Restores an archived database."""
    help = __doc__

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('archive_path', nargs='?', type=str)

        parser.add_argument(
            '--categories',
            action='store_true',
            help='Remove empty cateogires.',
        )

        parser.add_argument(
            '--backup_dir',
            default='/home/django/backups/database',
            help='The directory that is searched for archive files.',
        )

    def handle(self, *args, **options):
        """The method that is run when the commandline is invoked."""
        
        if options['categories']:
            for category in Category.objects.all():
                if category.count() == 0:
                    category.delete()
        print("Done")
