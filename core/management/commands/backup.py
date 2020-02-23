"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       core/management/command/backup.py
@copyright  GNU Public License, 2018
@authors    Frank Imeson
@brief      A managment script for backing up the database
"""


# *******************************************************************************
# Imports
# *******************************************************************************
import os
import re
import socket

from datetime import datetime

from django.core.management.base import BaseCommand


# *******************************************************************************
# Defines
# *******************************************************************************


# *******************************************************************************
# Methods
# *******************************************************************************


class Command(BaseCommand):
    """Backup the database to an archive."""
    help = __doc__

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('archive_path', nargs='?', type=str)

        # Named (optional) arguments
        parser.add_argument(
            '--site',
            choices=['wiki-o', 'wiki-x'],
            help='Choose which site the archive must come from.',
        )

        parser.add_argument(
            '--backup_dir',
            default='/home/django/backups/database',
            help='The directory that will be used to store the archive\
                  (not used if a path is provided).',
        )

    def handle(self, *args, **options):
        """The method that is run when the commandline is invoked."""

        # Check that postgress username/password is setup.
        if not os.environ.get('PGUSER') or not os.environ.get('PGPASSWORD'):
            s = "Error: PGUSER and or PGPASSWORD environment variable does not exist!\n"
            s += "       Please populate the username and password for postgresql."
            print(s)
            return

        # Auto construct the archive name.
        archive_path = options['archive_path']
        if archive_path is None:
            date = datetime.now().strftime('%Y.%m.%d')
            site = options['site']
            if site is None:
                site = socket.getfqdn()
                if re.search('wiki-o', site):
                    site = 'wiki-o'
                elif re.search('wiki-x', site):
                    site = 'wiki-x'
                else:
                    site = 'local'
            archive_path = '%s/%s - %s.sql' % (options['backup_dir'], date, site)

        # Backup the database (large archives should not be loaded into python).
        user = os.environ.get('PGUSER')
        pg_cmd = 'pg_dump -h localhost --username=%s -w wiki_o --file="%s"' % (user, archive_path)
        print('Saving backup to: %s.gz' % archive_path)
        os.system(pg_cmd)
        os.system('gzip -9 "%s"' % archive_path)
        print("Done")
