"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       users/apps.py
@brief      A collection of app specific configurations
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# imports
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
