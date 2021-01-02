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
from django.urls import path, register_converter
from theories.converters import CONTENT_PK_CYPHER
from theories.views import *

register_converter(CONTENT_PK_CYPHER, 'b64')

# *******************************************************************************
# urls
# *******************************************************************************
app_name = 'theories'
urlpatterns = [
    path('media/opinion<int:pk>.png', image_view, name='media01'),
    path('categories/', category_index_view, name='categories'),
    path('theories/', theory_index_view, name='index'),
    path('theories/<slug:category_slug>/', theory_index_view, name='theories'),
    path('theories/create/<slug:category_slug>/', theory_create_view, name='theory-create'),
    path('theories/<slug:category_slug>/activity/', activity_view, name='activity'),
    path('theory/pk_<b64:content_pk>/', theory_detail_view, name='theory-detail'),
    path('theory/pk_<b64:content_pk>/edit/', theory_edit_view, name='theory-edit'),
    path('theory/pk_<b64:content_pk>/merge/', theory_merge_view, name='theory-merge'),
    path('theory/pk_<b64:content_pk>/report/', theory_report_view, name='theory-report'),
    path('theory/pk_<b64:content_pk>/backups/', theory_backup_view, name='theory-backup'),
    path('theory/pk_<b64:content_pk>/restore/', theory_restore_view, name='theory-restore'),
    path('theory/pk_<b64:content_pk>/activity/', theory_activity_view, name='theory-activity'),
    path('theory/pk_<b64:content_pk>/edit_evidence/',
         theory_edit_evidence_view,
         name='theory-edit-evidence'),
    path('theory/pk_<b64:content_pk>/edit_subtheories/',
         theory_edit_subtheories_view,
         name='theory-edit-subtheories'),
    path('theory/<b64:content_pk01>/inherit/<b64:content_pk02>/',
         theory_inherit_view,
         name='theory-inherit'),
    path('theory/pk_<b64:content_pk>/del/', content_delete_redirect_view, name='theory-delete'),
    path('theory/pk_<b64:content_pk>/remove/', content_remove_redirect_view, name='theory-remove'),
    path('theory/pk_<b64:content_pk>/convert/',
         content_convert_redirect_view,
         name='theory-convert'),
    path('theory/pk_<b64:content_pk>/revert/<int:version_id>/',
         content_revert_redirect_view,
         name='theory-revert'),
    path('theory/pk_<b64:content_pk>/swap_titles/',
         content_swap_titles_redirect_view,
         name='theory-swap-titles'),
    path('evidence/<b64:content_pk>/', evidence_detail_view, name='evidence-detail'),
    path('evidence/<b64:content_pk>/edit/', evidence_edit_view, name='evidence-edit'),
    path('evidence/<b64:content_pk>/merge/', evidence_merge_view, name='evidence-merge'),
    path('evidence/<b64:content_pk>/report/', evidence_report_view, name='evidence-report'),
    path('evidence/<b64:content_pk>/restore/', evidence_restore_view, name='evidence-restore'),
    path('evidence/<b64:content_pk>/activity/', evidence_activity_view, name='evidence-activity'),
    path('evidence/<b64:content_pk>/del/', content_delete_redirect_view, name='evidence-delete'),
    path('evidence/<b64:content_pk>/remove/', content_remove_redirect_view, name='evidence-remove'),
    path('evidence/<b64:content_pk>/backup/', content_backup_redirect_view, name='evidence-backup'),
    path('evidence/<b64:content_pk>/convert/',
         content_convert_redirect_view,
         name='evidence-convert'),
    path('evidence/<b64:content_pk>/revert/<int:version_id>/',
         content_revert_redirect_view,
         name='evidence-revert'),
    path('theory/pk_<b64:content_pk>/opinions_<slug:opinion_slug>/',
         opinion_index_view,
         name='opinion-index'),
    path('theory/pk_<b64:content_pk>/opinion/pk_<b64:opinion_pk>/',
         theory_detail_view,
         name='theory-detail'),
    path('theory/pk_<b64:content_pk>/opinion/slug_<slug:opinion_slug>/',
         theory_detail_view,
         name='theory-detail'),
    path('theory/pk_<b64:content_pk>/analysis/pk_<b64:opinion_pk>/',
         opinion_analysis_view,
         name='opinion-analysis'),
    path('theory/pk_<b64:content_pk>/analysis/slug_<slug:opinion_slug>/',
         opinion_analysis_view,
         name='opinion-analysis'),
    path('opinion/<b64:content_pk>/edit/', opinion_edit_view, name='opinion-edit'),
    path('opinion/<b64:content_pk>/wizard/', opinion_wizard_view, name='opinion-wizard'),
    path('opinion/<b64:content_pk>/my_editor/',
         opinion_retrieve_my_editor_redirect_view,
         name='opinion-my-editor'),
    path('theory/pk_<b64:content_pk>/my_opinion/',
         retrieve_my_opinion_redirect_view,
         name='get_my_opinion'),
    path('theory/pk_<b64:content_pk>/my_opinion_stats/',
         retrieve_my_opinion_stats_redirect_view,
         name='get_my_opinion_stats'),
    path('opinion/<b64:opinion_pk>/del/', opinion_delete_redirect_view, name='opinion-delete'),
    path('opinion/<b64:opinion_pk>/copy/', opinion_copy_view, name='opinion-copy'),
    path('opinion/<b64:opinion_pk>/hide/',
         opinion_hide_user_redirect_view,
         name='opinion-hide-user'),
    path('opinion/<b64:opinion_pk>/unhide/',
         opinion_reveal_user_redirect_view,
         name='opinion-reveal-user'),
    path(
        'theory/pk_<b64:content_pk>/opinion/slug_<slug:opinion_slug01>/vs/slug_<slug:opinion_slug02>/',
        opinion_compare_view,
        name='opinion-compare'),
    path('theory/pk_<b64:content_pk>/opinion/slug_<slug:opinion_slug01>/vs/pk_<b64:opinion_pk02>/',
         opinion_compare_view,
         name='opinion-compare'),
    path('theory/pk_<b64:content_pk>/opinion/pk_<b64:opinion_pk01>/vs/slug_<slug:opinion_slug02>/',
         opinion_compare_view,
         name='opinion-compare'),
    path('theory/pk_<b64:content_pk>/opinion/pk_<b64:opinion_pk01>/vs/pk_<b64:opinion_pk02>/',
         opinion_compare_view,
         name='opinion-compare'),
]
