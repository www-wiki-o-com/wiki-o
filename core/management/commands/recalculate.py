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
from theories.models.opinions import OpinionDependency
from theories.models.statistics import (Stats, StatsDependency,
                                        StatsFlatDependency)

# *******************************************************************************
# Defines
# *******************************************************************************

# *******************************************************************************
# Methods
# *******************************************************************************


class Command(BaseCommand):
    """Recalculates the stats stored within the databse."""
    help = __doc__

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('primary_keys',
                            nargs='*',
                            type=int,
                            help='A set of theory keys to recaculate the stats for.')

    def handle(self, *args, **options):
        """The method that is run when the commandline is invoked."""

        if options['primary_keys']:
            thoeries = Content.objects.filter(pk__in=options['primary_keys'])
        else:
            thoeries = Content.objects.all()

        # Recalculate stats
        for theory in thoeries:
            if theory.is_theory():
                Stats.recalculate(theory)

        # Recalculate ranks
        for dependency in StatsDependency.objects.all():
            dependency.save()
        for dependency in StatsFlatDependency.objects.all():
            dependency.save()
        for dependency in OpinionDependency.objects.all():
            dependency.save()

        print("Done")
