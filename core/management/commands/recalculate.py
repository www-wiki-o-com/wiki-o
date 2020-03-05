"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       core/management/command/recalculate.py
@copyright  GNU Public License, 2018
@authors    Frank Imeson
@brief      A managment script for recalculating stats stored within the database
"""

# *******************************************************************************
# Imports
# *******************************************************************************
from django.core.management.base import BaseCommand
from theories.models import TheoryNode

# *******************************************************************************
# Defines
# *******************************************************************************

# *******************************************************************************
# Methods
# *******************************************************************************


class Command(BaseCommand):
    """Runs a series to recalculate the stats stored within the databse."""
    help = __doc__

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('primary_keys',
                            nargs='*',
                            type=int,
                            help='A set of theory primary keys to recaculate the stats for.')

    def handle(self, *args, **options):
        """The method that is run when the commandline is invoked."""

        if options['primary_keys']:
            thoeries = TheoryNode.objects.filter(pk__in=options['primary_keys'])
        else:
            thoeries = TheoryNode.objects.all()

        # Recalculate stats.
        for theory in thoeries:
            if theory.is_theory():
                theory.recalculate_stats()
            else:
                print("recalculate.py (error): pk=%d does not correspond to a theory." % theory.pk)

        print("Done")
