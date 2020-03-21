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
from django.contrib import admin
from reversion.admin import VersionAdmin
from theories.models import Category, Content, Opinion, OpinionNode
from theories.models import Stats, StatsNode, StatsFlatNode

# *******************************************************************************
# Classes
# *******************************************************************************


class CategoryAdmin(admin.ModelAdmin):
    pass


@admin.register(Content)
class ContentAdmin(VersionAdmin):
    pass


class OpinionAdmin(admin.ModelAdmin):

    def get_list_display(self, request):
        return ('user', 'theory')


class OpinionNodeAdmin(admin.ModelAdmin):

    def get_user(self, obj):
        return obj.parent.user

    get_user.short_description = 'User'

    def get_list_display(self, request):
        return ('get_user', 'content')


class StatsAdmin(admin.ModelAdmin):

    def get_list_display(self, request):
        return ('stats_type', 'theory')


class StatsNodeAdmin(admin.ModelAdmin):

    def get_owner(self, obj):
        return obj.parent.get_owner()

    get_owner.short_description = 'Type'

    def get_list_display(self, request):
        return ('get_owner', 'content')


class StatsFlatNodeAdmin(admin.ModelAdmin):

    def get_owner(self, obj):
        return obj.parent.get_owner()

    get_owner.short_description = 'Type'

    def get_list_display(self, request):
        return ('get_owner', 'content')


# *******************************************************************************
# register
# *******************************************************************************
#admin.site.register(Content, ContentAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Opinion, OpinionAdmin)
admin.site.register(OpinionNode, OpinionNodeAdmin)
admin.site.register(Stats, StatsAdmin)
admin.site.register(StatsNode, StatsNodeAdmin)
admin.site.register(StatsFlatNode, StatsFlatNodeAdmin)
