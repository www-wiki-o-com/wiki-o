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
