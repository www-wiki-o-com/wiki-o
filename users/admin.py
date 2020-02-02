"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       users/admin.py
@brief      The set of models that appear on the admin page
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""

from django.contrib import admin

from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group
from .models import *


# ************************************************************
#
# ************************************************************
class MyUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'hidden']
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {
            'fields': ('hidden'),
        }),
    )

    # ******************************
    #
    # ******************************

    def __str__(self):
        return 'blah' + self.username


admin.site.register(User, MyUserAdmin)
admin.site.register(Violation)
admin.site.register(ViolationVote)
admin.site.register(ViolationFeedback)
