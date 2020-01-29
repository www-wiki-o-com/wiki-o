# *******************************************************************************
# Wiki-O: A web service for sharing opinions and avoiding arguments.
# Copyright (C) 2018 Frank Imeson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# *******************************************************************************


# *******************************************************************************
# imports
# *******************************************************************************
import logging
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from users.models import User


# *******************************************************************************
# defines
# *******************************************************************************
logger = logging.getLogger(__name__)


# *******************************************************************************
# methods
# *******************************************************************************


# ******************************
# https://stackoverflow.com/questions/22250352/programmatically-create-a-django-group-with-permissions
# ******************************
def create_groups_and_permissions():
    group, created = Group.objects.get_or_create(name='user level: 0')
    for x in ['change', 'add', 'delete']:
        for y in ['opinion']:
            name = '%s_%s' % (x, y)
            ct = ContentType.objects.get(app_label='theories', model=y)
            perm, created = Permission.objects.get_or_create(
                content_type=ct, codename=name)
            group.permissions.add(perm)
            if created:
                logger.info('Created %s permissions.' % perm)
    for level in range(1, 5):
        group, created = Group.objects.get_or_create(
            name='user level: %d' % level)
        for x in ['change', 'add', 'delete', 'view']:
            for y in ['category', 'theorynode', 'opinion']:
                name = '%s_%s' % (x, y)
                ct = ContentType.objects.get(app_label='theories', model=y)
                perm, created = Permission.objects.get_or_create(
                    content_type=ct, codename=name)
                group.permissions.add(perm)
                if created:
                    logger.info('Created %s permissions.' % perm)
    logger.info('Created default group and permissions.')


# *******************************************************************************
# testing methods
#
#
#
#
#
#
#
#
#
#
# *******************************************************************************


# ******************************
#
# ******************************
def create_test_user(username='bob', password='1234', level=None):
    user = User.objects.create_user(
        username=username,
        password=password,
    )
    if level is not None:
        if level == 0:
            user.demote(new_level=level)
        if level > 1:
            user.promote(new_level=level)
    return user
