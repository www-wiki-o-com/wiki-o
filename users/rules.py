#*******************************************************************************
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
#*******************************************************************************


#*******************************************************************************
# imports
#*******************************************************************************
import rules
from rules.contrib.views import permission_required, objectgetter
from rules.contrib.views import PermissionRequiredMixin
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver

from .models import *
from theories.models import *


#*******************************************************************************
# Promotions/Demotions
#*******************************************************************************

#******************************
# Automatically add new users to level: 0
#******************************
@receiver(models.signals.post_save, sender=User)
def post_save_user_signal_handler(sender, instance, created, **kwargs):
    if created:
        group, created = Group.objects.get_or_create(name='user level: 1')
        instance.groups.add(group)
        instance.save()     


#*******************************************************************************
# Permissions
#*******************************************************************************


#*******************************************************************************
# predicates
  # https://github.com/dfunckt/django-rule
  # https://cheat.readthedocs.io/en/latest/django/permissions.html
  # https://stackoverflow.com/questions/41821921/model-field-level-permission-and-field-value-level-permission-in-django-and-drf
#*******************************************************************************
has_level00 = rules.is_group_member('user level: 0')
has_level01 = rules.is_group_member('user level: 1')
has_level02 = rules.is_group_member('user level: 2')
has_level03 = rules.is_group_member('user level: 3')
has_level04 = rules.is_group_member('user level: 4')


#******************************
# 
#******************************
@rules.predicate
def can_report(user, obj):
    if user.is_authenticated:
        if isinstance(obj, TheoryNode):
            if has_level00(user):
                return False
            else:
                return True
        elif isinstance(obj, Violation):
            if has_level03(user):
                return True
            elif has_level04(user):
                return True
    return False

#******************************
# 
#******************************
@rules.predicate
def can_vote(user, obj):
    if isinstance(obj, Violation) and user.is_authenticated and obj.is_polling():
        if has_level03(user) and user != obj.offender:
            return True
        elif has_level04(user):
            return True
    return False

#******************************
# 
#******************************
@rules.predicate
def can_comment(user, obj):
    if isinstance(obj, Violation) and user.is_authenticated:
        if has_level03(user) and obj.is_open():
            return True
        elif has_level04(user):
            return True
    return False


#*******************************************************************************
# permissions
#   Quirk: the methods defined below that utilize two arguments are only called
#          when two arguments are given?
#   Example: if user.has_perm('theories.change_title', theory)
#*******************************************************************************
rules.set_perm('users.can_vote_violation',              can_vote)
rules.set_perm('users.can_report_violation',            can_report)
rules.set_perm('users.can_comment_violation',           can_comment)
rules.set_perm('users.can_resolve_violation',           has_level04)




