"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       theories/admin.py
@brief      The set of models that appear on the admin page
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""

# *******************************************************************************
# Imports
# *******************************************************************************
from django.contrib import admin
from reversion.admin import VersionAdmin
from theories.models import Category, TheoryNode, Opinion, OpinionNode
from theories.models import Stats, StatsNode, StatsFlatNode

# *******************************************************************************
# Classes
# *******************************************************************************


# ************************************************************
#
# ************************************************************
class CategoryAdmin(admin.ModelAdmin):
    pass


# ************************************************************
#
# ************************************************************
@admin.register(TheoryNode)
class TheoryNodeAdmin(VersionAdmin):
    pass


# ************************************************************
#
# ************************************************************
class OpinionAdmin(admin.ModelAdmin):

    # ******************************
    #
    # ******************************
    def get_list_display(self, request):
        return ('user', 'theory')


# ************************************************************
#
# ************************************************************
class OpinionNodeAdmin(admin.ModelAdmin):

    # ******************************
    #
    # ******************************
    def get_user(self, obj):
        return obj.parent.user

    get_user.short_description = 'User'

    # ******************************
    #
    # ******************************
    def get_list_display(self, request):
        return ('get_user', 'theory_node')


# ************************************************************
#
# ************************************************************
class StatsAdmin(admin.ModelAdmin):

    # ******************************
    #
    # ******************************
    def get_list_display(self, request):
        return ('stats_type', 'theory')


# ************************************************************
#
# ************************************************************
class StatsNodeAdmin(admin.ModelAdmin):

    # ******************************
    #
    # ******************************
    def get_owner(self, obj):
        return obj.parent.get_owner()

    get_owner.short_description = 'Type'

    # ******************************
    #
    # ******************************
    def get_list_display(self, request):
        return ('get_owner', 'theory_node')


# ************************************************************
#
# ************************************************************
class StatsFlatNodeAdmin(admin.ModelAdmin):

    # ******************************
    #
    # ******************************
    def get_owner(self, obj):
        return obj.parent.get_owner()

    get_owner.short_description = 'Type'

    # ******************************
    #
    # ******************************
    def get_list_display(self, request):
        return ('get_owner', 'theory_node')


# *******************************************************************************
# register
# *******************************************************************************
#admin.site.register(TheoryNode, TheoryNodeAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Opinion, OpinionAdmin)
admin.site.register(OpinionNode, OpinionNodeAdmin)
admin.site.register(Stats, StatsAdmin)
admin.site.register(StatsNode, StatsNodeAdmin)
admin.site.register(StatsFlatNode, StatsFlatNodeAdmin)
