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
from django.apps import AppConfig


class TheoriesConfig(AppConfig):
    """Class representing a Django application and its configuration."""

    name = 'theories'

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('Opinion'))
        registry.register(self.get_model('Category'))
        registry.register(self.get_model('Content'))
