r""" __      __    __               ___
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
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin
from invitations.utils import get_invitation_model
from invitations.admin import InvitationAdmin

from users.models import User, Violation, ViolationFeedback, ViolationVote


class MyUserAdmin(UserAdmin):
    """A custom admin model for User.

    Attributes:
        list_display (list[str]): Todo
        add_fieldsets (): Todo
    """

    list_display = ['username', 'email', 'hidden']
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {
        'fields': ('hidden'),
    }),)

    def __str__(self):
        """Returns the user's handle.

        Returns:
            str: The user's handle.
        """
        return self.username


admin.site.register(User, MyUserAdmin)
admin.site.register(Violation)
admin.site.register(ViolationVote)
admin.site.register(ViolationFeedback)
admin.site.unregister(get_invitation_model())


class InvitationsAdmin(AdminSite):
    site_header = "Invitations"
    site_title = "v"
    index_title = "Welcome to Invitations Portal"


invitation_admin_site = InvitationsAdmin(name='invitation_admin')
invitation_admin_site.register(get_invitation_model(), InvitationAdmin)
