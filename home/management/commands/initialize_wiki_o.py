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
from users.utils import create_groups_and_permissions
from theories.utils import create_categories, create_reserved_nodes


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
        create_groups_and_permissions()
        create_categories()
        site = Site.objects.first()
        site.domain = 'wiki-o.com'
        site.name   = 'Wiki-O'
        site.save()




