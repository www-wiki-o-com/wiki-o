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


from django.contrib import admin

from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group
from .models import *



#************************************************************
# 
#************************************************************
class MyUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'hidden']
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {
            'fields': ('hidden'),
        }),
    )


    #******************************
    # 
    #******************************
    def __str__(self):
        return 'blah' + self.username


admin.site.register(User, MyUserAdmin)
admin.site.register(Violation)
admin.site.register(ViolationVote)
admin.site.register(ViolationFeedback)

