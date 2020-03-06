"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       theories/apps.py
@brief      A collection of app specific configurations
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""

# *******************************************************************************
# Imports
# *******************************************************************************
from django.apps import AppConfig


# ************************************************************
#
# ************************************************************
class TheoriesConfig(AppConfig):
    name = 'theories'

    # ******************************
    #
    # ******************************
    def ready(self):
        from actstream import registry
        registry.register(self.get_model('Opinion'))
        registry.register(self.get_model('Category'))
        registry.register(self.get_model('TheoryNode'))
