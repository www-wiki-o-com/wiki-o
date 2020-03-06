"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE file in the root directory of this source tree.
"""

# *******************************************************************************
# Imports
# *******************************************************************************
from django.apps import AppConfig


# ************************************************************
#
# ************************************************************
class UsersConfig(AppConfig):
    name = 'users'

    # ******************************
    #
    # ******************************
    def ready(self):
        from actstream import registry
        registry.register(self.get_model('User'))
