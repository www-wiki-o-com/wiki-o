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

from theories.models import TheoryNode, Opinion
from reversion.models import Version


#*******************************************************************************
# ToDos:
#   - update update update
  # add num_contributers to theory_node
  # 
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
def is_author(user, obj):
    if user.is_authenticated:
        if isinstance(obj, TheoryNode):
            return obj.created_by == user
        elif isinstance(obj, Opinion):
            return obj.user == user
        elif isinstance(obj, Version):
            return obj.revision.user == user  

#******************************
# 
#******************************
@rules.predicate
def can_edit_title(user, obj=None):
    if isinstance(obj, TheoryNode) and user.is_authenticated:
        utilization = obj.get_utilization(user)
        if has_level00(user):
            return False
        elif has_level01(user) and utilization == 0 and is_author(user,obj):
            return True
        elif has_level02(user) and utilization <= 10:
            return True
        elif has_level03(user) and utilization <= 100:
            return True
        elif has_level04(user):
            return True
    return False    

#******************************
# 
#******************************
@rules.predicate
def can_edit_details(user, obj):
    if has_level00(user):
        return False
    return True

#******************************
# 
#******************************
@rules.predicate
def can_remove(user, obj):
    if isinstance(obj, TheoryNode) and user.is_authenticated:
        utilization = obj.get_utilization(user)
        if has_level00(user):
            return False
        elif has_level01(user) and utilization == 0 and is_author(user, obj):
            return True
        elif has_level02(user) and utilization <= 10:
            return True
        elif has_level03(user) and utilization <= 100:
            return True
        elif has_level04(user):
            return True
    return False

#******************************
# 
#******************************
@rules.predicate
def can_delete(user, obj):
    if isinstance(obj, TheoryNode) and user.is_authenticated:
        utilization = obj.get_utilization(user)
        if has_level00(user):
            return False
        elif has_level01(user) and utilization == 0 and is_author(user, obj):
            return True
        elif has_level04(user):
            return True
    return False

#******************************
# 
#******************************
@rules.predicate
def can_restore(user, obj):
    if has_level04(user):
        return True
    return False


#*******************************************************************************
# permissions
#   Quirk: the methods defined below that utilize two arguments are only called
#          when two arguments are given?
#   Example: if user.has_perm('theories.change_title', theory)
#*******************************************************************************

# theories/evidence
rules.set_perm('theories.change_details',     can_edit_details)
rules.set_perm('theories.change_theorynode',  can_edit_details)

rules.set_perm('theories.change_title',       can_edit_title)
rules.set_perm('theories.swap_title',         can_edit_title)
rules.set_perm('theories.merge_theorynode',   can_edit_title)
rules.set_perm('theories.convert_theorynode', can_edit_title)

rules.set_perm('theories.remove_theorynode',  can_remove)
rules.set_perm('theories.delete_theorynode',  can_delete)

# opinions
rules.set_perm('theories.change_opinion',     is_author)
rules.set_perm('theories.delete_opinion',     is_author)

# revisions
rules.set_perm('theories.delete_reversion',   has_level04)
rules.set_perm('theories.backup_theorynode',  has_level04)
rules.set_perm('theories.restore_theorynode', has_level04)

# report
rules.set_perm('theories.report',             has_level01)




