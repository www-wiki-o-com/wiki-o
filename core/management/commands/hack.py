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
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from actstream.models import Action
from reversion.models import Version
from notifications.models import Notification

from users.models import User, Violation
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

    def add_arguments(self, parser):
        parser.add_argument(
            '--report01',
            help='Change ownership of all theory nodes.',
        )

        parser.add_argument(
            '--report02',
            help='Change ownership of all violations.',
        )

    def handle(self, *args, **options):
        """The method that is run when the commandline is invoked."""
        if options['report01']:
            self.report01(options['report01'])
        if options['report02']:
            self.report02(options['report02'])
        print('done')

    def report01(self, username):
        user = User.objects.get(username=username)
        for theory_node in TheoryNode.objects.all():
            theory_node.created_by = user
            theory_node.modified_by = user
            theory_node.save()
        for version in Version.objects.all():
            version.revision.user = user
            version.revision.save()
        for violation in Violation.objects.all():
            violation.offender = user
            violation.save()

    def report02(self, username):
        user = User.objects.get(username=username)
        for violation in Violation.objects.all():
            violation.offender = user
            violation.save()

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
