"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       users/utils.py
@brief      A collection of app specific utility methods/classes
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# Imports
# *******************************************************************************
from django.contrib.auth.models import Group


# *******************************************************************************
# Methods
# *******************************************************************************

def get_group(level):
    """Get the user group corresponding to the level.

    Args:
        level (int): The level.

    Returns:
        Group: The user group.
    """
    return Group.objects.get(name='user level: %d' % level)
