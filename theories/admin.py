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

from theories.models.categories import Category
from theories.models.opinions import Opinion, OpinionDependency
from theories.models.statistics import Stats, StatsDependency, StatsFlatDependency

# *******************************************************************************
# Classes
# *******************************************************************************


class CategoryAdmin(admin.ModelAdmin):
    pass


class OpinionAdmin(admin.ModelAdmin):

    @classmethod
    def get_list_display(cls, request):
        return ('user', 'theory')


class OpinionDependencyAdmin(admin.ModelAdmin):

    @classmethod
    def get_user(cls, obj):
        return obj.parent.user

    get_user.short_description = 'User'

    @classmethod
    def get_list_display(cls, request):
        return ('get_user', 'content')


class StatsAdmin(admin.ModelAdmin):

    @classmethod
    def get_list_display(cls, request):
        return ('stats_type', 'theory')


class StatsDependencyAdmin(admin.ModelAdmin):

    @classmethod
    def get_owner(cls, obj):
        return obj.parent.get_owner()

    get_owner.short_description = 'Type'

    @classmethod
    def get_list_display(cls, request):
        return ('get_owner', 'content')


class StatsFlatDependencyAdmin(admin.ModelAdmin):

    @classmethod
    def get_owner(cls, obj):
        return obj.parent.get_owner()

    get_owner.short_description = 'Type'

    @classmethod
    def get_list_display(cls, request):
        return ('get_owner', 'content')


# *******************************************************************************
# register
# *******************************************************************************
admin.site.register(Category, CategoryAdmin)
admin.site.register(Opinion, OpinionAdmin)
admin.site.register(OpinionDependency, OpinionDependencyAdmin)
admin.site.register(Stats, StatsAdmin)
admin.site.register(StatsDependency, StatsDependencyAdmin)
admin.site.register(StatsFlatDependency, StatsFlatDependencyAdmin)
