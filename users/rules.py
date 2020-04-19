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
import rules
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from theories.models.content import Content
from users.models import User, Violation

# *******************************************************************************
# Promotions/Demotions
# *******************************************************************************


@receiver(post_save, sender=User)
def post_save_user_signal_handler(sender, instance, created, **kwargs):
    """Automatically add new users to group "level: 0".

    Args:
        sender ([type]): [description]
        instance ([type]): [description]
        created ([type]): [description]
    """
    if created:
        group, _created = Group.objects.get_or_create(name='user level: 1')
        instance.groups.add(group)
        instance.save()


# *******************************************************************************
# Permissions
# *******************************************************************************

# *******************************************************************************
# predicates
# https://github.com/dfunckt/django-rule
# https://cheat.readthedocs.io/en/latest/django/permissions.html
# https://stackoverflow.com/questions/41821921/model-field-level-permission-and-field-value-level-permission-in-django-and-drf
# *******************************************************************************
HAS_LEVEL00 = rules.is_group_member('user level: 0')
HAS_LEVEL01 = rules.is_group_member('user level: 1')
HAS_LEVEL02 = rules.is_group_member('user level: 2')
HAS_LEVEL03 = rules.is_group_member('user level: 3')
HAS_LEVEL04 = rules.is_group_member('user level: 4')


@rules.predicate
def can_report(user, obj):
    if user.is_authenticated:
        if isinstance(obj, Content):
            if HAS_LEVEL00(user):
                return False
            return True
        if isinstance(obj, Violation):
            if HAS_LEVEL03(user):
                return True
            if HAS_LEVEL04(user):
                return True
    return False


@rules.predicate
def can_vote(user, obj):
    if isinstance(obj, Violation) and user.is_authenticated and obj.is_open():
        if HAS_LEVEL03(user) and user != obj.offender:
            return True
        if HAS_LEVEL04(user):
            return True
    return False


@rules.predicate
def can_comment(user, obj):
    if isinstance(obj, Violation) and user.is_authenticated:
        if HAS_LEVEL03(user) and obj.is_open():
            return True
        if HAS_LEVEL04(user):
            return True
    return False


# *******************************************************************************
# permissions
#   Quirk: the methods defined below that utilize two arguments are only called
#          when two arguments are given?
#   Example: if user.has_perm('theories.change_title', theory)
# *******************************************************************************
rules.set_perm('users.can_vote_violation', can_vote)
rules.set_perm('users.can_report_violation', can_report)
rules.set_perm('users.can_comment_violation', can_comment)
rules.set_perm('users.can_resolve_violation', HAS_LEVEL04)  # Todo: not working.
