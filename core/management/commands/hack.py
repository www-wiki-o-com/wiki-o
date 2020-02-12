"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       core/management/hack.py
@brief      A debug script for updating the database
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# Imports
# *******************************************************************************
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from actstream.models import Action
from reversion.models import Version
from notifications.models import Notification

from users.models import User
from theories.models import TheoryNode


# *******************************************************************************
# Defines
# *******************************************************************************


# *******************************************************************************
# Methods
# *******************************************************************************


class Command(BaseCommand):
    """Updates permissions, categories, and site."""
    help = __doc__

    def handle(self, *args, **options):
        """The method that is run when the commandline is invoked."""
        self.fix_modified_by()
        print('done')

    def fix_modified_by(self):
        """Fixes the modified by field."""
        system = User.objects.get(username='system')
        for theory_node in TheoryNode.objects.all():
            theory_node.modified_by = system
            theory_node.save()

    def fix_permissions(self):
        """Fixes the set of permissions."""
        for permission in Permission.objects.all():
            if str(permission.content_type) == 'Theory Node':
                if permission.codename in ['add_edges', 'delete_edges']:
                    print('delete', permission.codename)
                    permission.delete()

    def fix_ownerships(self):
        """Fixes any objects with broken ownership."""
        fcimeson = User.objects.get(username='fcimeson')
        for theory_node in TheoryNode.objects.filter(created_by__isnull=True):
            theory_node.created_by = fcimeson
            theory_node.save()

    def delete_revisions(self):
        """Delete's all revisions."""
        for version in Version.objects.all():
            version.delete()

    def fix_action_streams(self):
        """Fixes all broken action stream messages."""
        for action in Action.objects.all():
            print('Action:', action)

    def fix_notifications(self):
        """Fix all broken notifications."""
        for notification in Notification.objects.all():
            print('Notification:', notification)
