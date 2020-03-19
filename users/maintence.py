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
import logging

from nose.tools import nottest
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from users.models import User

# *******************************************************************************
# Defines and Globals
# *******************************************************************************
LOGGER = logging.getLogger(__name__)

# *******************************************************************************
# Methods
# *******************************************************************************


def create_groups_and_permissions(max_level=4):
    """Create the set of groups and permissions used by Wiki-O.

    This method is used for unit tests and the initial setup of Wiki-O's database. This method
    will not remove permissions add through the admin interface.
    """

    # Create the user level groups.
    for level in range(max_level + 1):
        group, created = Group.objects.get_or_create(name='user level: %d' % level)
        if created:
            LOGGER.info('Created user level: %d.', level)

    # Add basic permissions for user level groups (the additional restrictions are accomplished
    # using rules).
    for level in range(max_level + 1):
        group = Group.objects.get(name='user level: %d' % level)
        for x in ['change', 'add', 'delete', 'view']:
            if level == 0:
                content = ['opinion']
            else:
                content = ['category', 'theorynode', 'opinion']
            for y in content:
                name = '%s_%s' % (x, y)
                content_type = ContentType.objects.get(app_label='theories', model=y)
                perm, created = Permission.objects.get_or_create(content_type=content_type,
                                                                 codename=name)
                group.permissions.add(perm)
                if created:
                    LOGGER.info('Created %s permissions.', perm)

    LOGGER.info('Created default group and permissions.')


@nottest
def create_test_user(username='bob', password='1234', level=None):
    """Create a test user.

    Args:
        username (str, optional): The user's name. Defaults to 'bob'.
        password (str, optional): The user's password. Defaults to '1234'.
        level (int, optional): The user's permission level. Defaults to None.

    Returns:
        User: The user.
    """
    user = User.objects.create_user(
        username=username,
        password=password,
    )
    if level is not None:
        if user.get_level() > level:
            user.demote(new_level=level)
        elif user.get_level() < level:
            user.promote(new_level=level)
    return user
