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
import logging
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.contrib.auth.models import Group, Permission

from users.models import User
from actstream.models import Action
from reversion.models import Version
from theories.models import TheoryNode
from notifications.models import Notification



#*******************************************************************************
# defines
#*******************************************************************************



#*******************************************************************************
# methods
#*******************************************************************************


#************************************************************
# 
#************************************************************
class Command(BaseCommand):
    help = 'Updates permissions, categories, and site.'

    #******************************
    # 
    #******************************
    def handle(self, *args, **options):
    
        # fix permissions
#        for permission in Permission.objects.all():
#            if str(permission.content_type) == 'Theory Node':
#                if permission.codename in ['add_edges', 'delete_edges']:
#                    print('delete', permission.codename)
#                    permission.delete()
        
        # fix ownership
#        fcimeson = User.objects.get(username='fcimeson')
#        for theory_node in TheoryNode.objects.filter(created_by__isnull=True):
#            theory_node.created_by = fcimeson
#            theory_node.save()

        # fix modified by
        fcimeson = User.objects.get(username='fcimeson')
        system   = User.objects.get(username='system')
        for theory_node in TheoryNode.objects.all():
            theory_node.modified_by = system
            theory_node.save()
        
        # fix revisions
#        for version in Version.objects.all():
#            version.delete()
        
        # fix action streams
#        fcimeson = User.objects.get(username='fcimeson')
#        for action in Action.objects.all():
#            print('Action:', action)
        
        # fix notifications
#        for notification in Notification.objects.all():
#            print('Notification:', notification)
        
        print('done')




