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
from django.contrib import admin
from reversion.admin import VersionAdmin
from .models import *



#*******************************************************************************
# classes
#*******************************************************************************


#************************************************************
# 
#************************************************************
class CategoryAdmin(admin.ModelAdmin):
    pass


#************************************************************
# 
#************************************************************
@admin.register(TheoryNode)
class TheoryNodeAdmin(VersionAdmin):
    pass


#************************************************************
# 
#************************************************************
class OpinionAdmin(admin.ModelAdmin):

    #******************************
    # 
    #******************************
    def get_list_display(self, request):
        return ('user', 'theory')


#************************************************************
# 
#************************************************************
class OpinionNodeAdmin(admin.ModelAdmin):

    #******************************
    # 
    #******************************
    def get_user(self, obj):
        return obj.parent.user
    get_user.short_description = 'User'
        
    #******************************
    # 
    #******************************
    def get_list_display(self, request):
        return ('get_user', 'theory_node')


#************************************************************
# 
#************************************************************
class StatsAdmin(admin.ModelAdmin):

    #******************************
    # 
    #******************************
    def get_list_display(self, request):
        return ('stats_type', 'theory')


#************************************************************
# 
#************************************************************
class StatsNodeAdmin(admin.ModelAdmin):

    #******************************
    # 
    #******************************
    def get_owner(self, obj):
        return obj.parent.get_owner()
    get_owner.short_description = 'Type'
        
    #******************************
    # 
    #******************************
    def get_list_display(self, request):
        return ('get_owner', 'theory_node')



#************************************************************
# 
#************************************************************
class StatsFlatNodeAdmin(admin.ModelAdmin):

    #******************************
    # 
    #******************************
    def get_owner(self, obj):
        return obj.parent.get_owner()
    get_owner.short_description = 'Type'
        
    #******************************
    # 
    #******************************
    def get_list_display(self, request):
        return ('get_owner', 'theory_node')




#*******************************************************************************
# register
#*******************************************************************************
#admin.site.register(TheoryNode,     TheoryNodeAdmin)
admin.site.register(Category,       CategoryAdmin)
admin.site.register(Opinion,        OpinionAdmin)
admin.site.register(OpinionNode,    OpinionNodeAdmin)
admin.site.register(Stats,          StatsAdmin)
admin.site.register(StatsNode,      StatsNodeAdmin)
admin.site.register(StatsFlatNode,  StatsFlatNodeAdmin)




