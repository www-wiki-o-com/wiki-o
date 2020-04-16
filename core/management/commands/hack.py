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
import random
import time

from actstream.models import Action
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand
from notifications.models import Notification
from reversion.models import Version

from core.converters import IntegerCypher
from theories.models.content import Content
from users.models import User, Violation

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
            help='Change ownership of all theory dependencies.',
        )

        parser.add_argument(
            '--report02',
            help='Change ownership of all violations.',
        )

        parser.add_argument(
            '--test01',
            action='store_true',
            help='Test cypher.',
        )

        parser.add_argument(
            '--test02',
            action='store_true',
            help='Test cypher.',
        )

    def handle(self, *args, **options):
        """The method that is run when the commandline is invoked."""
        if options['report01']:
            self.report01(options['report01'])
        if options['report02']:
            self.report02(options['report02'])
        if options['test01']:
            bit_length = 24
            cypher = IntegerCypher(bit_length=bit_length)
            start = time.time()
            for x00 in range(1000000):
                x00 = random.randint(0, 2**bit_length - 1)
                x01 = cypher.to_url(x00)
                x02 = cypher.to_python(x01)
                # print(x01)
                if x00 != x02:
                    print(
                        "IntegerCypher: Error, plain text -> cypher -> plain text failed: %d, %b, %d"
                        % (x00, x01, x02))
            end = time.time()
            print(end - start)
        if options['test02']:
            theory = Content.objects.get(pk=10)
            print(theory.url())
        print('done')

    def report01(self, username):
        user = User.objects.get(username=username)
        for content in Content.objects.all():
            content.created_by = user
            content.modified_by = user
            content.save()
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
        for content in Content.objects.all():
            content.modified_by = system
            content.save()

    def fix_permissions(self):
        """Fixes the set of permissions."""
        for permission in Permission.objects.all():
            if str(permission.content_type) == 'Content':
                if permission.codename in ['add_edges', 'delete_edges']:
                    print('delete', permission.codename)
                    permission.delete()

    def fix_ownerships(self):
        """Fixes any objects with broken ownership."""
        fcimeson = User.objects.get(username='fcimeson')
        for content in Content.objects.filter(created_by__isnull=True):
            content.created_by = fcimeson
            content.save()

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
