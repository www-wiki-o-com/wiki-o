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
import logging
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


def create_groups_and_permissions():
    """Create the set of groups and permissions used by Wiki-O.

    This method is used for unit tests and the initial setup of Wiki-O's database.
    """
    group, created = Group.objects.get_or_create(name='user level: 0')
    for x in ['change', 'add', 'delete']:
        for y in ['opinion']:
            name = '%s_%s' % (x, y)
            content_type = ContentType.objects.get(app_label='theories', model=y)
            perm, created = Permission.objects.get_or_create(content_type=content_type,
                                                             codename=name)
            group.permissions.add(perm)
            if created:
                LOGGER.info('Created %s permissions.', perm)
    for level in range(1, 5):
        group, created = Group.objects.get_or_create(name='user level: %d' % level)
        for x in ['change', 'add', 'delete', 'view']:
            for y in ['category', 'theorynode', 'opinion']:
                name = '%s_%s' % (x, y)
                content_type = ContentType.objects.get(app_label='theories', model=y)
                perm, created = Permission.objects.get_or_create(content_type=content_type,
                                                                 codename=name)
                group.permissions.add(perm)
                if created:
                    LOGGER.info('Created %s permissions.', perm)
    LOGGER.info('Created default group and permissions.')


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
        if level == 0:
            user.demote(new_level=level)
        if level >= 1:
            user.promote(new_level=level)
    return user
