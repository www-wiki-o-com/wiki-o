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


# *******************************************************************************
# Imports
# *******************************************************************************
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from users.models import User, Violation, ViolationVote, ViolationFeedback


class MyUserAdmin(UserAdmin):
    """A custom admin model for User.

    Attributes:
        list_display (list[str]): Todo
        add_fieldsets (): Todo
    """

    list_display = ['username', 'email', 'hidden']
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {
            'fields': ('hidden'),
        }),
    )

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
