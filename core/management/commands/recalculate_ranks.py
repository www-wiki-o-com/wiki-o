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
from theories.models.opinions import OpinionDependency
from theories.models.statistics import StatsDependency, StatsFlatDependency

# *******************************************************************************
# Defines
# *******************************************************************************

# *******************************************************************************
# Methods
# *******************************************************************************


class Command(BaseCommand):
    """Recalculates the ranks stored within the databse."""
    help = __doc__

    def handle(self, *args, **options):
        """The method that is run when the commandline is invoked."""

        for dependency in StatsDependency.objects.all():
            dependency.save()
        for dependency in StatsFlatDependency.objects.all():
            dependency.save()
        for dependency in OpinionDependency.objects.all():
            dependency.save()

        print("Done")
