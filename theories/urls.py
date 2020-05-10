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
from django.urls import path, register_converter
from theories.converters import CONTENT_PK_CYPHER
from theories.views import *

register_converter(CONTENT_PK_CYPHER, 'b64')

# *******************************************************************************
# urls
# *******************************************************************************
app_name = 'theories'
urlpatterns = [
    path('media/opinion<int:pk>.png', ImageView, name='media01'),
    path('categories/', CategoryIndexView, name='categories'),
    path('theories/', TheoryIndexView, name='index'),
    path('theories/<slug:category_slug>/', TheoryIndexView, name='theories'),
    path('theories/create/<slug:category_slug>/', TheoryCreateView, name='theory-create'),
    path('theories/<slug:category_slug>/activity/', ActivityView, name='activity'),
    path('theory/<b64:content_pk>/', TheoryDetail, name='theory-detail'),
    path('theory/<b64:content_pk>/edit/', TheoryEditView, name='theory-edit'),
    path('theory/<b64:content_pk>/merge/', TheoryMergeView, name='theory-merge'),
    path('theory/<b64:content_pk>/report/', TheoryReportView, name='theory-report'),
    path('theory/<b64:content_pk>/backups/', TheoryBackupView, name='theory-backup'),
    path('theory/<b64:content_pk>/restore/', TheoryRestoreView, name='theory-restore'),
    path('theory/<b64:content_pk>/activity/', TheoryActivityView, name='theory-activity'),
    path('theory/<b64:content_pk>/edit_evidence/',
         TheoryEditEvidenceView,
         name='theory-edit-evidence'),
    path('theory/<b64:content_pk>/edit_subtheories/',
         TheoryEditSubtheoriesView,
         name='theory-edit-subtheories'),
    path('theory/<b64:content_pk01>/inherit/<b64:content_pk02>/',
         TheoryInheritView,
         name='theory-inherit'),
    path('theory/<b64:content_pk>/del/', ContentDelete, name='theory-delete'),
    path('theory/<b64:content_pk>/remove/', ContentRemove, name='theory-remove'),
    path('theory/<b64:content_pk>/convert/', ContentConvert, name='theory-convert'),
    path('theory/<b64:content_pk>/revert/<int:version_id>/', RevertContent, name='theory-revert'),
    path('theory/<b64:content_pk>/swap_titles/', TheorySwapTitles, name='theory-swap-titles'),
    path('evidence/<b64:content_pk>/', EvidenceDetail, name='evidence-detail'),
    path('evidence/<b64:content_pk>/edit/', EvidenceEditView, name='evidence-edit'),
    path('evidence/<b64:content_pk>/merge/', EvidenceMergeView, name='evidence-merge'),
    path('evidence/<b64:content_pk>/report/', EvidenceReportView, name='evidence-report'),
    path('evidence/<b64:content_pk>/restore/', EvidenceRestoreView, name='evidence-restore'),
    path('evidence/<b64:content_pk>/activity/', EvidenceActivityView, name='evidence-activity'),
    path('evidence/<b64:content_pk>/del/', ContentDelete, name='evidence-delete'),
    path('evidence/<b64:content_pk>/remove/', ContentRemove, name='evidence-remove'),
    path('evidence/<b64:content_pk>/backup/', BackupContent, name='evidence-backup'),
    path('evidence/<b64:content_pk>/convert/', ContentConvert, name='evidence-convert'),
    path('evidence/<b64:content_pk>/revert/<int:version_id>/',
         RevertContent,
         name='evidence-revert'),
    path('theory/<b64:content_pk>/opinions_<slug:opinion_slug>/',
         OpinionIndexView,
         name='opinion-index'),
    path('theory/<b64:content_pk>/opinion/pk_<b64:opinion_pk>/',
         OpinionDetailView,
         name='opinion-detail'),
    path('theory/<b64:content_pk>/opinion/slug_<slug:opinion_slug>/',
         OpinionDetailView,
         name='opinion-detail'),
    path('opinion/<b64:content_pk>/edit/', OpinionEditView, name='opinion-edit'),
    path('opinion/<b64:content_pk>/wizard/', OpinionWizardView, name='opinion-wizard'),
    path('opinion/<b64:content_pk>/my_editor/', RetrieveMyOpinionEditor, name='opinion-my-editor'),
    path('theory/<b64:content_pk>/my_opinion/', RetrieveMyOpinion, name='get_my_opinion'),
    path('opinion/<b64:opinion_pk>/del/', OpinionDelete, name='opinion-delete'),
    path('opinion/<b64:opinion_pk>/copy/', OpinionCopy, name='opinion-copy'),
    path('opinion/<b64:opinion_pk>/hide/', OpinionHideUser, name='opinion-hide-user'),
    path('opinion/<b64:opinion_pk>/unhide/', OpinionRevealUser, name='opinion-reveal-user'),
    path(
        'theory/<b64:content_pk>/opinion/slug_<slug:opinion_slug01>/vs/slug_<slug:opinion_slug02>/',
        OpinionCompareView,
        name='opinion-compare'),
    path('theory/<b64:content_pk>/opinion/slug_<slug:opinion_slug01>/vs/pk_<b64:opinion_pk02>/',
         OpinionCompareView,
         name='opinion-compare'),
    path('theory/<b64:content_pk>/opinion/pk_<b64:opinion_pk01>/vs/slug_<slug:opinion_slug02>/',
         OpinionCompareView,
         name='opinion-compare'),
    path('theory/<b64:content_pk>/opinion/pk_<b64:opinion_pk01>/vs/pk_<b64:opinion_pk02>/',
         OpinionCompareView,
         name='opinion-compare'),
]
