"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE.md file in the root directory of this source tree.
"""

# *******************************************************************************
# Imports
# *******************************************************************************
from django.core.management.base import BaseCommand
from theories.models.content import Content
from theories.models.statistics import Stats

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
            thoeries = Content.objects.filter(pk__in=options['primary_keys'])
        else:
            thoeries = Content.objects.all()

        # Recalculate stats.
        for theory in thoeries:
            if theory.is_theory():
                Stats.recalculate(theory)
            else:
                print("recalculate.py (error): pk=%d does not correspond to a theory." % theory.pk)

        print("Done")
