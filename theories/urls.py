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
from django.urls import path
from theories.views import *

# *******************************************************************************
# urls
# *******************************************************************************
app_name = 'theories'
urlpatterns = [
    path('media/opinion<int:pk>.png', ImageView, name='media01'),
    path('categories/', CategoryIndexView, name='categories'),
    path('theories/', TheoryIndexView, name='index'),
    path('theories/<slug:cat>/', TheoryIndexView, name='theories'),
    path('theories/create/<slug:cat>/', TheoryCreateView, name='theory-create'),
    path('theories/<slug:cat>/activity/', ActivityView, name='activity'),
    path('theory/<int:pk>/', TheoryDetail.as_view(), name='theory-detail'),
    path('theory/<int:pk>/edit/', TheoryEditView, name='theory-edit'),
    path('theory/<int:pk>/merge/', TheoryMergeView, name='theory-merge'),
    path('theory/<int:pk>/report/', TheoryReportView, name='theory-report'),
    path('theory/<int:pk>/backups/', TheoryBackupView, name='theory-backup'),
    path('theory/<int:pk>/restore/', TheoryRestoreView, name='theory-restore'),
    path('theory/<int:pk>/activity/', TheoryActivityView, name='theory-activity'),
    path('theory/<int:pk>/edit_evidence/', TheoryEditEvidenceView, name='theory-edit-evidence'),
    path('theory/<int:pk>/edit_subtheories/',
         TheoryEditSubtheoriesView,
         name='theory-edit-subtheories'),
    path('theory/<int:pk01>/inherit/<int:pk02>/', TheoryInheritView, name='theory-inherit'),
    path('theory/<int:pk>/del/', TheoryNodeDelete, name='theory-delete'),
    path('theory/<int:pk>/remove/', TheoryNodeRemove, name='theory-remove'),
    path('theory/<int:pk>/convert/', TheoryNodeConvert, name='theory-convert'),
    path('theory/<int:pk>/revert/<int:vid>/', RevertTheoryNode, name='theory-revert'),
    path('theory/<int:pk>/swap_titles/', TheorySwapTitles, name='theory-swap-titles'),
    path('theory/<int:pk>/add_to_home', TheoryAddToHome, name='theory-add-to-home'),
    path('theory/<int:pk>/remove_from_home', TheoryRemoveFromHome, name='theory-remove-from-home'),
    path('evidence/<int:pk>/', EvidenceDetail.as_view(), name='evidence-detail'),
    path('evidence/<int:pk>/edit/', EvidenceEditView, name='evidence-edit'),
    path('evidence/<int:pk>/merge/', EvidenceMergeView, name='evidence-merge'),
    path('evidence/<int:pk>/report/', EvidenceReportView, name='evidence-report'),
    path('evidence/<int:pk>/restore/', EvidenceRestoreView, name='evidence-restore'),
    path('evidence/<int:pk>/activity/', EvidenceActivityView, name='evidence-activity'),
    path('evidence/<int:pk>/del/', TheoryNodeDelete, name='evidence-delete'),
    path('evidence/<int:pk>/remove/', TheoryNodeRemove, name='evidence-remove'),
    path('evidence/<int:pk>/backup/', BackupTheoryNode, name='evidence-backup'),
    path('evidence/<int:pk>/convert/', TheoryNodeConvert, name='evidence-convert'),
    path('evidence/<int:pk>/revert/<int:vid>/', RevertTheoryNode, name='evidence-revert'),
    path('theory/<int:pk>/opinions_<slug:slug>/', OpinionIndexView, name='opinion-index'),
    path('theory/<int:pk>/opinion/<slug:slug>/', OpinionDetailView, name='opinion-detail'),
    path('opinion/<int:pk>/edit/', OpinionEditView, name='opinion-edit'),
    path('opinion/<int:pk>/wizard/', OpinionWizardView, name='opinion-wizard'),
    path('opinion/<int:pk>/my_editor/', RetrieveMyOpinionEditor, name='opinion-my-editor'),
    path('theory/<int:pk>/my_opinion/', RetrieveMyOpinion, name='get_my_opinion'),
    path('opinion/<int:pk>/del/', OpinionDelete, name='opinion-delete'),
    path('opinion/<int:pk>/copy/', OpinionCopy, name='opinion-copy'),
    path('opinion/<int:pk>/hide/', OpinionHideUser, name='opinion-hide-user'),
    path('opinion/<int:pk>/unhide/', OpinionRevealUser, name='opinion-reveal-user'),
    path('theory/<int:pk>/opinion/<slug:slug01>_vs_<slug:slug02>/',
         OpinionCompareView,
         name='opinion-compare'),
]
