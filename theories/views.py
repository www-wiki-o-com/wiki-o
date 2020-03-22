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
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse
from django.template import loader
from django.views import generic
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.views.generic import TemplateView
from django.forms import Textarea, modelformset_factory
from django.views.generic.base import RedirectView
from django.core import mail
from django.db.models import Count, Sum, F, Q
from rules.contrib.views import permission_required
from rules.contrib.views import objectgetter as get_object
from rules.contrib.views import PermissionRequiredMixin
from django.utils.http import unquote
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth.models import Group, Permission
from django.http import Http404

import re
import copy
import inspect
import datetime
import reversion
import unicodedata
from reversion.models import Version
from actstream import action
from actstream.models import user_stream, model_stream, target_stream, followers
from actstream.actions import is_following
from notifications.signals import notify

from theories.converters import CONTENT_PK_CYPHER
from theories.models import Category, Content, Opinion, OpinionDependency, Stats
from theories.forms import TheoryForm, EvidenceForm, OpinionForm
from theories.forms import SelectDependencyForm, OpinionDependencyForm
from theories.forms import TheoryRevisionForm, EvidenceRevisionForm
from theories.graphs.pie_charts import OpinionPieChart
from theories.graphs.pie_charts import OpinionComparisionPieChart
from theories.graphs.pie_charts import DemoPieChart
from theories.graphs.bar_graphs import OpinionBarGraph
from theories.graphs.bar_graphs import OpinionComparisionBarGraph
from theories.graphs.bar_graphs import DemoBarGraph
from theories.graphs.venn_diagrams import OpinionVennDiagram
from theories.graphs.venn_diagrams import OpinionComparisionVennDiagram
from theories.graphs.venn_diagrams import DemoVennDiagram
from theories.utils import get_demo_opinion
from theories.utils import get_category_suggestions

from users.models import User
from users.forms import ReportViolationForm
from core.utils import Parameters, get_or_none, get_page_list

# *******************************************************************************
# Defines
# *******************************************************************************
MAX_NUM_PAGES = 5
NUM_ITEMS_PER_PAGE = 25

# *******************************************************************************
# Methods
# *******************************************************************************


def get_opinion_list(theory, current_user, exclude_list=[]):
    """Generate a list of opinions based on the current user. The output is a list of dictionary
       items: text, true_points, false_points, and url."""

    # setup
    opinion_list = []
    exclude_users = []
    for x in exclude_list:
        if isinstance(x, User) and x.is_authenticated:
            exclude_users.append(x)

    # my opinion
    if current_user.is_authenticated and current_user not in exclude_users:
        if 'my_opinion' not in exclude_list:
            entry = {
                'text': 'My Opinion',
                'true_points': 0,
                'false_points': 0,
                'url': reverse('theories:get_my_opinion', kwargs={'content_pk': theory.pk}),
            }
            my_opinion = get_or_none(theory.opinions, user=current_user)
            if my_opinion is not None:
                entry['true_points'] = round(my_opinion.true_points() * 100)
                entry['false_points'] = round(my_opinion.false_points() * 100)
            opinion_list.append(entry)
            exclude_users.append(current_user)

    # stats
    for stats in theory.stats.all():
        if stats.stats_type not in exclude_list and stats.total_points() > 0:
            entry = {
                'text': stats.get_owner(),
                'true_points': round(stats.true_points() * 100),
                'false_points': round(stats.false_points() * 100),
                'url': stats.url(),
            }
            opinion_list.append(entry)

    # other opinions
    for opinion in theory.opinions.exclude(user__in=exclude_users)[:10]:
        opinion_list.append({
            'text': opinion.get_owner(),
            'true_points': round(opinion.true_points() * 100),
            'false_points': round(opinion.false_points() * 100),
            'url': opinion.url(),
        })

    return opinion_list


def get_compare_list(opinion01, current_user, exclude_list=[]):
    """Generate a list of comparisons based on the current opinion and current
       user. The output is a list of dictionary items: text, true_points,
       false_points, and url."""

    # setup
    theory = opinion01.content
    compare_list = []
    exclude_users = []
    for x in exclude_list:
        if isinstance(x, User) and x.is_authenticated:
            exclude_users.append(x)
    if hasattr(opinion01, 'user'):
        exclude_users.append(opinion01.user)

    # my opinion
    if current_user.is_authenticated and current_user not in exclude_users:
        my_opinion = get_or_none(theory.opinions, user=current_user)
        if 'my_opinion' not in exclude_list and my_opinion is not None:
            entry = {
                'text': 'My Opinion',
                'true_points': round(my_opinion.true_points() * 100),
                'false_points': round(my_opinion.false_points() * 100),
                'url': opinion01.compare_url(my_opinion),
            }
            compare_list.append(entry)
            exclude_users.append(current_user)

    # stats
    for stats in theory.stats.all():
        if stats.stats_type not in exclude_list and stats.total_points() > 0:
            entry = {
                'text': stats.get_owner(),
                'true_points': round(stats.true_points() * 100),
                'false_points': round(stats.false_points() * 100),
                'url': opinion01.compare_url(stats),
            }
            compare_list.append(entry)

    # other opinions
    for opinion02 in theory.opinions.exclude(user__in=exclude_users)[:10]:
        compare_list.append({
            'text': opinion02.get_owner(),
            'true_points': round(opinion02.true_points() * 100),
            'false_points': round(opinion02.false_points() * 100),
            'url': opinion01.compare_url(opinion02),
        })

    return compare_list


# *******************************************************************************
# Categories views
# *******************************************************************************


def ActivityView(request, category_slug=None):
    """Home view for display all root theories."""

    # Setup
    user = request.user
    date = request.GET.get('date', None)

    # Category
    if category_slug is None:
        category = get_object_or_404(Category, slug='all')
    else:
        category = get_object_or_404(Category, slug=category_slug)
    categories = Category.get_all().exclude(pk=category.pk)
    subscribed = user.is_authenticated and is_following(user, category)

    # Actions
    if date is None:
        actions = category.target_actions.exclude(verb='started following')
    else:
        date = unquote(date)
        actions = category.target_actions.exclude(verb='started following').filter(
            timestamp__gte=date)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(actions, NUM_ITEMS_PER_PAGE)
    actions = paginator.get_page(page)
    actions.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request)

    # Render
    context = {
        'category': category,
        'actions': actions,
        'categories': categories,
        'subscribed': subscribed,
        'date_filter': date,
        'params': params,
    }
    return render(
        request,
        'theories/activity_index.html',
        context,
    )


def CategoryIndexView(request):
    """Index view for categories.

    Args:
        request ([type]): The post request data.
    """

    # Params
    params = Parameters(request)

    # Categories
    search_term = request.GET.get('search', '')
    if len(search_term) > 0:
        categories = Category.objects.filter(title__icontains=search_term)
    else:
        categories = Category.objects.all()
    categories = list(categories)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(categories, NUM_ITEMS_PER_PAGE * 3)
    categories = paginator.get_page(page)
    categories.page_list = get_page_list(paginator.num_pages, page)

    # Render
    context = {
        'categories': categories,
        'params': params,
    }
    return render(
        request,
        'theories/category_index.html',
        context,
    )


# *******************************************************************************
# Theory views
# *******************************************************************************


def TheoryIndexView(request, category_slug=None):
    """Home view for display all root theories."""

    # Categories
    if category_slug is None:
        category = get_object_or_404(Category, title='All')
    else:
        category = get_object_or_404(Category, slug=category_slug)
    categories = Category.get_all().exclude(pk=category.pk)[:6]

    # Theories
    search_term = request.GET.get('search', '')
    if len(search_term) > 0:
        theories = category.get_theories().filter(title01__icontains=search_term)
    else:
        theories = category.get_theories()

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(theories, NUM_ITEMS_PER_PAGE)
    theories = paginator.get_page(page)
    theories.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request)

    # Render
    context = {
        'theories': theories,
        'category': category,
        'categories': categories,
        'params': params,
    }
    return render(
        request,
        'theories/theory_index.html',
        context,
    )


def TheoryDetail(request, content_pk):
    """A view for displaying theory details."""
    # Preconditions
    Content.update_intuition()

    # Setup
    theory = get_object_or_404(Content, pk=content_pk)
    deleted = theory.is_deleted()
    parent_theories = theory.get_parent_theories(deleted=deleted)
    theory_dependencies = theory.get_dependencies(deleted=deleted).exclude(pk=Content.INTUITION_PK)

    opinions = {}
    opinions['supporters'] = get_or_none(theory.stats, stats_type=Stats.TYPE.SUPPORTERS)
    opinions['moderates'] = get_or_none(theory.stats, stats_type=Stats.TYPE.MODERATES)
    opinions['opposers'] = get_or_none(theory.stats, stats_type=Stats.TYPE.OPPOSERS)
    opinions['all'] = get_or_none(theory.stats, stats_type=Stats.TYPE.ALL)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(theory_dependencies, NUM_ITEMS_PER_PAGE)
    theory_dependencies = paginator.get_page(page)
    theory_dependencies.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(theory.pk))
    if len(params.path) > 0:
        pk = CONTENT_PK_CYPHER.to_python(params.path[-1])
        parent_theory = get_object_or_404(Content, pk=pk)
        prev = parent_theory.url() + params.get_prev()
    else:
        prev = reverse('theories:index') + params

    # Hit counts
    theory.update_hits(request)

    # Context
    context = {
        'theory': theory,
        'theory_dependencies': theory_dependencies,
        'parent_theories': parent_theories,
        'opinions': opinions,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/theory_detail.html',
        context,
    )


@login_required
@permission_required('theories.add_content', raise_exception=True)
def TheoryCreateView(request, category_slug):
    """View for create a new theory."""

    # Setup
    user = request.user
    category = get_object_or_404(Category, slug=category_slug)

    # Navigation
    params = Parameters(request)
    prev = reverse('theories:index') + params

    # Post request
    if request.method == 'POST':
        form = TheoryForm(request.POST,
                          user=user,
                          show_categories=True,
                          initial_categories=category.title)
        if form.is_valid():
            theory = form.save()
            theory.update_activity_logs(user, verb=form.get_verb())
            return redirect(theory.url() + params)
    # Get request
    else:
        form = TheoryForm(user=user, show_categories=True, initial_categories=category.title)

    # Render
    context = {
        'edit': False,
        'category_list': Category.objects.all(),
        'category_suggestions': get_category_suggestions(),
        'category': category,
        'form': form,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/theory_edit.html',
        context,
    )


@login_required
@permission_required('theories.change_content',
                     fn=get_object(Content, 'content_pk'),
                     raise_exception=True)
def TheoryEditView(request, content_pk):
    """A view for editing theory details."""

    # Setup
    user = request.user
    theory = get_object_or_404(Content, pk=content_pk)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        pk = CONTENT_PK_CYPHER.to_python(params.path[0])
        root_theory = get_object_or_404(Content, pk=pk)
    else:
        root_theory = theory

    # Post request
    if request.method == 'POST':
        form = TheoryForm(request.POST, instance=theory, user=user, show_categories=True)
        if form.is_valid():
            categories_before = set(theory.get_categories())
            theory = form.save()
            categories_after = set(theory.get_categories())
            for category in categories_before - categories_after:
                category.update_activity_logs(user,
                                              verb='Removed <# object.url {{ object }} #>',
                                              action_object=theory)
            for category in categories_after - categories_before:
                category.update_activity_logs(user,
                                              verb='Added <# object.url {{ object }} #>',
                                              action_object=theory)
            theory.update_activity_logs(user, verb=form.get_verb())
            return redirect(next)

    # Get request
    else:
        form = TheoryForm(instance=theory, user=user, show_categories=True)

    # Render
    context = {
        'edit': True,
        'category_list': Category.objects.all(),
        'category_suggestions': get_category_suggestions(),
        'root_theory': root_theory,
        'theory': theory,
        'form': form,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/theory_edit.html',
        context,
    )


@login_required
@permission_required('theories.add_content', raise_exception=True)
def TheoryEditEvidenceView(request, content_pk):
    """A view for editing evidence details for the pertaining theory."""

    # Setup
    user = request.user
    theory = get_object_or_404(Content, pk=content_pk)
    evidence_list = theory.get_theory_evidence()
    EvidenceFormSet = modelformset_factory(Content, form=EvidenceForm, extra=3)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(evidence_list, NUM_ITEMS_PER_PAGE)
    evidence_list = paginator.get_page(page)
    evidence_list.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        pk = CONTENT_PK_CYPHER.to_python(params.path[0])
        root_theory = get_object_or_404(Content, pk=pk)
    else:
        root_theory = theory

    # Post request
    if request.method == 'POST':
        formset = EvidenceFormSet(request.POST,
                                  queryset=evidence_list.object_list,
                                  form_kwargs={'user': user})
        if formset.is_valid():
            for form in formset:
                if form.has_changed():
                    # save
                    evidence = form.save()
                    # update dependencies
                    theory.add_dependency(evidence)
                    # activity log
                    evidence.update_activity_logs(user, form.get_verb())
            return redirect(prev)
        else:
            print(238, formset.errors)

    # Get request
    else:
        formset = EvidenceFormSet(queryset=evidence_list.object_list, form_kwargs={'user': user})

    # Render
    context = {
        'root_theory': root_theory,
        'theory': theory,
        'formset': formset,
        'evidence_list': evidence_list,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/theory_edit_evidence.html',
        context,
    )


@login_required
@permission_required('theories.add_content', raise_exception=True)
def TheoryEditSubtheoriesView(request, content_pk):
    """A view for editing sub-theory details for the pertaining theory."""

    # Setup
    user = request.user
    theory = get_object_or_404(Content, pk=content_pk)
    subtheory_list = theory.get_theory_subtheories()
    SubTheoryFormSet = modelformset_factory(Content, form=TheoryForm, extra=3)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(subtheory_list, NUM_ITEMS_PER_PAGE)
    subtheory_list = paginator.get_page(page)
    subtheory_list.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        pk = CONTENT_PK_CYPHER.to_python(params.path[0])
        root_theory = get_object_or_404(Content, pk=pk)
    else:
        root_theory = theory

    # Post request
    if request.method == 'POST':
        formset = SubTheoryFormSet(request.POST,
                                   queryset=subtheory_list.object_list,
                                   form_kwargs={'user': user})
        if formset.is_valid():
            for form in formset:
                if form.has_changed():
                    # save
                    subtheory = form.save()
                    # update dependencies
                    theory.add_dependency(subtheory)
                    # activity log
                    subtheory.update_activity_logs(user, verb=form.get_verb())
            return redirect(next)
        else:
            print(220, formset.errors)

    # Get request
    else:
        formset = SubTheoryFormSet(queryset=subtheory_list.object_list, form_kwargs={'user': user})

    # Render
    context = {
        'root_theory': root_theory,
        'theory': theory,
        'formset': formset,
        'subtheory_list': subtheory_list,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/theory_edit_subtheories.html',
        context,
    )


@login_required
@permission_required('theories.merge_content',
                     fn=get_object(Content, 'content_pk'),
                     raise_exception=True)
def TheoryMergeView(request, content_pk):
    """A view for merging theories."""

    # Setup
    user = request.user
    theory = get_object_or_404(Content, pk=content_pk)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        parent_pk = CONTENT_PK_CYPHER.to_python(params.path[-1])
        root_pk = CONTENT_PK_CYPHER.to_python(params.path[0])
        parent_theory = get_object_or_404(Content, pk=parent_pk)
        root_theory = get_object_or_404(Content, pk=root_pk)
    else:
        parent_theory = theory
        root_theory = theory

    # Setup cont'd
    candidates = parent_theory.get_nested_subtheory_dependencies().filter(
        content_type=theory.content_type).exclude(pk=theory.pk)
    MergeFormSet = modelformset_factory(Content, form=SelectDependencyForm, extra=0)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(candidates, NUM_ITEMS_PER_PAGE * 4)
    candidates = paginator.get_page(page)
    candidates.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Post request
    if request.method == 'POST':
        formset = MergeFormSet(request.POST, queryset=candidates.object_list)
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data['select']:
                    content = form.instance
                    # merge
                    theory.merge(content, user=user)
                    # activity log
                    theory.update_activity_logs(user,
                                                verb='Merged with <# object.url {{ object }} #>',
                                                action_object=content)
            return redirect(next)
        else:
            print(200, formset.errors)

    # Get request
    else:
        formset = MergeFormSet(queryset=candidates.object_list)

    # Render
    context = {
        'root_theory': root_theory,
        'theory': theory,
        'formset': formset,
        'candidates': candidates,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/theory_edit_merge.html',
        context,
    )


@login_required
@permission_required('theories.add_edge', raise_exception=True)
def TheoryInheritView(request, content_pk01, content_pk02):
    """A view for inheriting evidence/sub-theories into the pertaining theory."""

    # Setup
    user = request.user
    theory = get_object_or_404(Content, pk=content_pk01)
    root_theory = get_object_or_404(Content, pk=content_pk02)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk01))
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    search_term = request.GET.get('search', '')
    path_content_pks = [CONTENT_PK_CYPHER.to_python(x) for x in params.path] + [theory.pk]
    root_theory_dependencies = root_theory.get_nested_dependencies().exclude(
        pk=Content.INTUITION_PK)
    root_theory_dependencies = root_theory_dependencies | Content.objects.filter(pk=root_theory.pk)
    candidates = root_theory_dependencies.exclude(pk__in=theory.get_dependencies())
    candidates = candidates.exclude(pk__in=path_content_pks)
    if len(search_term) > 0:
        filtered_candidates = candidates.filter(title01__icontains=search_term)
        if filtered_candidates.count() > 0:
            candidates = filtered_candidates
    exclude_other = root_theory_dependencies.values_list('pk', flat=True)
    other_theories = Category.get('All').get_theories().exclude(pk__in=exclude_other)
    if len(search_term) > 0:
        filtered_other_theories = other_theories.filter(title01__icontains=search_term)
        if filtered_other_theories.count() > 0:
            other_theories = filtered_other_theories
    InheritFormSet = modelformset_factory(Content, form=SelectDependencyForm, extra=0)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(candidates, NUM_ITEMS_PER_PAGE * 4)
    candidates = paginator.get_page(page)
    candidates.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Post request
    if request.method == 'POST':
        formset = InheritFormSet(request.POST, queryset=candidates.object_list)
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data['select']:
                    dependency = form.instance
                    # inherit
                    theory.add_dependency(dependency)
                    # activity log
                    theory.update_activity_logs(user,
                                                verb='Inherited <# object.url {{ object }} #>',
                                                action_object=dependency)
            return redirect(next)

    # Get request
    else:
        formset = InheritFormSet(queryset=candidates.object_list)

    # Render
    context = {
        'root_theory': root_theory,
        'theory': theory,
        'other_theories': other_theories,
        'formset': formset,
        'candidates': candidates,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/theory_edit_inherit.html',
        context,
    )


@login_required
@permission_required('theories.change_content', raise_exception=True)
def TheoryRestoreView(request, content_pk):
    """A view for reviewing/deleting theory revisions."""

    # Setup
    user = request.user
    theory = get_object_or_404(Content, pk=content_pk)
    revisions = theory.get_revisions()
    RevisionFormSet = modelformset_factory(Version, form=TheoryRevisionForm, extra=0)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(revisions, NUM_ITEMS_PER_PAGE)
    revisions = paginator.get_page(page)
    revisions.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        pk = CONTENT_PK_CYPHER.to_python(params.path[0])
        root_theory = get_object_or_404(Content, pk=pk)
    else:
        root_theory = theory

    # Post request
    if request.method == 'POST':
        formset = RevisionFormSet(request.POST,
                                  queryset=revisions.object_list,
                                  form_kwargs={'user': user})
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data['delete']:
                    version = form.instance
                    if user.has_perm('theories.delete_reversion', version):
                        # delete
                        version.delete()
                        # activity log
                        theory.update_activity_logs(user, verb='Revision (deleted)')
            return redirect(next)
        else:
            print(200, formset.errors)
            print(201, request.POST)

    # Get request
    else:
        formset = RevisionFormSet(queryset=revisions.object_list, form_kwargs={'user': user})

    # Render
    context = {
        'root_theory': root_theory,
        'theory': theory,
        'formset': formset,
        'revisions': revisions,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/theory_edit_restore.html',
        context,
    )


@login_required
@permission_required('theories.backup_content', raise_exception=True)
def TheoryBackupView(request, content_pk):
    """A method for taking a snap-shot (backup) of a theory dependency."""

    # Setup
    user = request.user
    theory = get_object_or_404(Content, pk=content_pk)
    candidates = Content.objects.filter(pk=theory.pk) | theory.get_nested_dependencies()
    candidates = candidates.exclude(pk=Content.INTUITION_PK)
    BackupFormSet = modelformset_factory(Content, form=SelectDependencyForm, extra=0)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(candidates, NUM_ITEMS_PER_PAGE * 4)
    candidates = paginator.get_page(page)
    candidates.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        pk = CONTENT_PK_CYPHER.to_python(params.path[0])
        root_theory = get_object_or_404(Content, pk=pk)
    else:
        root_theory = theory

    # Post request
    if request.method == 'POST':
        formset = BackupFormSet(request.POST, queryset=candidates.object_list)
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data['select']:
                    content = form.instance
                    content.save_snapshot(user)
            return redirect(next)
        else:
            print(200, formset.errors)

    # Get request
    else:
        formset = BackupFormSet(queryset=candidates.object_list)

    # Render
    context = {
        'root_theory': root_theory,
        'theory': theory,
        'formset': formset,
        'candidates': candidates,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/theory_edit_backup.html',
        context,
    )


def TheoryReportView(request, content_pk):

    # Setup
    user = request.user
    theory = get_object_or_404(Content, pk=content_pk)
    open_violations = theory.get_violations(is_open=True, is_closed=False)
    closed_violations = theory.get_violations(is_open=False, is_closed=True)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        pk = CONTENT_PK_CYPHER.to_python(params.path[0])
        root_theory = get_object_or_404(Content, pk=pk)
    else:
        root_theory = theory

    # Post request
    if request.method == 'POST':

        # debug
        print('\n\n\n')
        print(request.POST)
        print('\n\n\n')

        form = ReportViolationForm(request.POST, user=user, content=theory)
        if form.is_valid():
            report = form.save()
            if report.offender == theory.modified_by:
                theory.autosave(user, force=True)
            return redirect(next)
        else:
            print(1000, form.errors)

    # Get request
    else:
        form = ReportViolationForm(user=user, content=theory)

    # Render
    context = {
        'root_theory': root_theory,
        'theory': theory,
        'open_violations': open_violations,
        'closed_violations': closed_violations,
        'form': form,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/theory_edit_report.html',
        context,
    )


def TheoryActivityView(request, content_pk):
    """A view for theory activity."""

    # Setup
    user = request.user
    date = request.GET.get('date', None)
    theory = get_object_or_404(Content, pk=content_pk)
    subscribed = user.is_authenticated and is_following(user, theory)

    # Filter
    if date is None:
        actions = theory.target_actions.exclude(verb='started following')
    else:
        date = unquote(date)
        actions = theory.target_actions.exclude(verb='following').filter(timestamp__gte=date)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(actions, NUM_ITEMS_PER_PAGE)
    actions = paginator.get_page(page)
    actions.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        pk = CONTENT_PK_CYPHER.to_python(params.path[0])
        root_theory = get_object_or_404(Content, pk=pk)
    else:
        root_theory = theory

    # Render
    context = {
        'root_theory': root_theory,
        'theory': theory,
        'actions': actions,
        'subscribed': subscribed,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/theory_edit_activity.html',
        context,
    )


# *******************************************************************************
# Evidence views
# *******************************************************************************


def EvidenceDetail(request, content_pk):
    """A view for displaying evidence details."""

    # Setup
    evidence = get_object_or_404(Content, pk=content_pk)
    parent_theories = evidence.get_parent_theories()

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    if len(params.path) > 0:
        pk = CONTENT_PK_CYPHER.to_python(params.path[-1])
        parent_theory = get_object_or_404(Content, pk=pk)
        prev = parent_theory.url() + params.get_prev()
    else:
        prev = reverse('theories:index') + params

    # Hit counts
    evidence.update_hits(request)

    # Context
    context = {
        'parent_theories': parent_theories,
        'evidence': evidence,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/evidence_detail.html',
        context,
    )


@login_required
@permission_required('theories.change_content',
                     fn=get_object(Content, 'content_pk'),
                     raise_exception=True)
def EvidenceEditView(request, content_pk):
    """A view for editing evidence details."""

    # Setup
    user = request.user
    evidence = get_object_or_404(Content, pk=content_pk)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = evidence.url() + params
    next = evidence.url() + params

    # Post request
    if request.method == 'POST':
        form = EvidenceForm(request.POST, instance=evidence, user=user)
        if form.is_valid():
            # save
            evidence = form.save()
            # activity log
            evidence.update_activity_logs(user, verb=form.get_verb())
            # redirect
            return redirect(next)
        else:
            print(226, form.errors)
    # Get request
    else:
        form = EvidenceForm(instance=evidence, user=user)

    # Render
    context = {
        'form': form,
        'evidence': evidence,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/evidence_edit.html',
        context,
    )


@login_required
@permission_required('theories.merge_content',
                     fn=get_object(Content, 'content_pk'),
                     raise_exception=True)
def EvidenceMergeView(request, content_pk):
    """A view for merging theories."""

    # Setup
    user = request.user
    evidence = get_object_or_404(Content, pk=content_pk)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = evidence.url() + params
    next = evidence.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        pk = CONTENT_PK_CYPHER.to_python(params.path[-1])
        parent_theory = get_object_or_404(Content, pk=pk)
    else:
        return redirect('theories:index')

    # Setup cont'd
    candidates = parent_theory.get_flat_dependencies().filter(content_type=evidence.content_type)
    candidates = candidates.exclude(pk=evidence.pk).exclude(pk=Content.INTUITION_PK)
    MergeFormSet = modelformset_factory(Content, form=SelectDependencyForm, extra=0)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(candidates, NUM_ITEMS_PER_PAGE * 4)
    candidates = paginator.get_page(page)
    candidates.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Post request
    if request.method == 'POST':
        formset = MergeFormSet(request.POST, queryset=candidates.object_list)
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data['select']:
                    content = form.instance
                    # merge
                    evidence.merge(content, user=user)
                    # activity log
                    evidence.update_activity_logs(user, verb='Merge', action_object=content)
            return redirect(next)
        else:
            print(200, formset.errors)

    # Get request
    else:
        formset = MergeFormSet(queryset=candidates.object_list)

    # Render
    context = {
        'evidence': evidence,
        'formset': formset,
        'candidates': candidates,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/evidence_edit_merge.html',
        context,
    )


@login_required
@permission_required('theories.change_content', raise_exception=True)
def EvidenceRestoreView(request, content_pk):
    """A view for reviewing evidence revisions."""

    # Setup
    user = request.user
    evidence = get_object_or_404(Content, pk=content_pk)
    revisions = evidence.get_revisions()
    RevisionFormSet = modelformset_factory(Version, form=EvidenceRevisionForm, extra=0)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(revisions, NUM_ITEMS_PER_PAGE)
    revisions = paginator.get_page(page)
    revisions.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = evidence.url() + params
    next = evidence.url() + params

    # Post request
    if request.method == 'POST':
        formset = RevisionFormSet(request.POST,
                                  queryset=revisions.object_list,
                                  form_kwargs={'user': user})
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data['delete']:
                    version = form.instance
                    if user.has_perm('theories.delete_reversion', version):
                        # delete
                        version.delete()
                        # activity log
                        evidence.update_activity_logs(user, verb='Revision (deleted)')
            return redirect(next)
        else:
            print(200, formset.errors)

    # Get request
    else:
        formset = RevisionFormSet(queryset=revisions.object_list, form_kwargs={'user': user})

    # Render
    context = {
        'evidence': evidence,
        'formset': formset,
        'revisions': revisions,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/evidence_edit_restore.html',
        context,
    )


def EvidenceReportView(request, content_pk):

    # Setup
    user = request.user
    evidence = get_object_or_404(Content, pk=content_pk)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = evidence.url() + params
    next = evidence.url() + params

    # Post request
    if request.method == 'POST':
        form = ReportViolationForm(request.POST, user=user, content=evidence)
        if form.is_valid():
            report = form.save()
            return redirect(next)
        else:
            print(1000, form.errors)

    # Get request
    else:
        form = ReportViolationForm(user=user, content=evidence)

    # Render
    context = {
        'evidence': evidence,
        'form': form,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/evidence_edit_report.html',
        context,
    )


def EvidenceActivityView(request, content_pk):
    """A view for evidence activity."""

    # Setup
    user = request.user
    date = request.GET.get('date', None)
    evidence = get_object_or_404(Content, pk=content_pk)
    subscribed = user.is_authenticated and is_following(user, evidence)

    # Filter
    if date is None:
        actions = evidence.target_actions.exclude(verb='started following')
    else:
        date = unquote(date)
        actions = evidence.target_actions.exclude(verb='following').filter(timestamp__gte=date)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(actions, NUM_ITEMS_PER_PAGE)
    actions = paginator.get_page(page)
    actions.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = evidence.url() + params
    next = evidence.url() + params

    # Render
    context = {
        'evidence': evidence,
        'actions': actions,
        'subscribed': subscribed,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/evidence_edit_activity.html',
        context,
    )


# *******************************************************************************
# Content Methods
# *******************************************************************************


@permission_required('theories.delete_edge',
                     fn=get_object(Content, 'content_pk'),
                     raise_exception=True)
def ContentRemove(request, content_pk):
    """A redirect for deleting theory dependency edges (removing from parents)."""

    # Setup
    user = request.user
    content = get_object_or_404(Content, pk=content_pk)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = content.url() + params
    if len(params.path) > 0:
        pk = CONTENT_PK_CYPHER.to_python(params.path[-1])
        parent_theory = get_object_or_404(Content, pk=pk)
        next = parent_theory.url() + params.get_prev()
    else:
        return reverse('theories:index')

    # Post request
    if request.method == 'POST':
        parent_theory.remove_dependency(content, user)
        parent_theory.update_activity_logs(user,
                                           verb='Removed <# object.url {{ object }} #>',
                                           action_object=content)
        # cleanup abandoned theory
        if content.parents.count() == 0 and not content.is_root():
            content.delete(user)
            content.update_activity_logs(user, verb='Deleted.')
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


@permission_required('theories.delete_content',
                     fn=get_object(Content, 'content_pk'),
                     raise_exception=True)
def ContentDelete(request, content_pk):
    """A redirect for deleting theory dependencies."""

    # Setup
    user = request.user
    content = get_object_or_404(Content, pk=content_pk)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = content.url() + params
    if len(params.path) > 0:
        pk = CONTENT_PK_CYPHER.to_python(params.path[-1])
        parent_theory = get_object_or_404(Content, pk=pk)
        next = parent_theory.url() + params.get_prev()
    else:
        parent_theory = None
        next = reverse('theories:index') + params

    # Post request
    if request.method == 'POST':
        content.delete(user)
        content.update_activity_logs(user, verb='Deleted')
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


@login_required
@permission_required('theories.backup_content', raise_exception=True)
def BackupContent(request, content_pk):
    """A method for taking a snap-shot (backup) of a theory dependency."""

    # Setup
    user = request.user
    content = get_object_or_404(Content, pk=content_pk)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = request.META.get('HTTP_REFERER', '/')
    next = request.META.get('HTTP_REFERER', '/')

    # Post request
    if request.method == 'POST':
        content.save_snapshot(user)
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


@permission_required('theories.restore_content',
                     fn=get_object(Content, 'content_pk'),
                     raise_exception=True)
def RevertContent(request, content_pk, version_id):
    """A method for restoring a theory-dependency snap-shot (backup)."""

    # Setup
    user = request.user
    content = get_object_or_404(Content, pk=content_pk)
    version = get_object_or_404(Version, id=version_id)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = request.META.get('HTTP_REFERER', '/')
    next = content.url() + params

    # Post request
    if request.method == 'POST':
        with reversion.create_revision():
            content.save()
            reversion.set_user(content.modified_by)
            reversion.set_comment('AutoSave - Revert')
        for key in version.field_dict.keys():
            setattr(content, key, version.field_dict[key])
        content.save()
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


@permission_required('theories.convert_content',
                     fn=get_object(Content, 'content_pk'),
                     raise_exception=True)
def ContentConvert(request, content_pk):
    """A method for converting a sub-theories to evidence and vise-a-versa."""

    # Setup
    user = request.user
    content = get_object_or_404(Content, pk=content_pk)
    verifiable = request.POST.get('verifiable') in ['True', 'yes']

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = content.url() + params
    if len(params.path) == 0:
        if content.is_root() or content.is_evidence():
            return redirect('theories:index')
    else:
        pk = CONTENT_PK_CYPHER.to_python(params.path[-1])
        parent_theory = get_object_or_404(Content, pk=pk)

    # Post request
    if request.method == 'POST':
        # convert
        content.convert(user, verifiable=verifiable)
        # activity
        if content.is_evidence():
            content.update_activity_logs(user, verb='Converted to Evidence')
        else:
            content.update_activity_logs(user, verb='Converted to Sub-Theory')
        next = content.url() + params
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


@permission_required('theories.swap_title',
                     fn=get_object(Content, 'content_pk'),
                     raise_exception=True)
def TheorySwapTitles(request, content_pk):
    """A redirect for swapping the theory true/false statements."""

    # Setup
    user = request.user
    theory = get_object_or_404(Content, pk=content_pk)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    prev = request.META.get('HTTP_REFERER', '/')
    next = request.META.get('HTTP_REFERER', '/')

    # Post request
    if request.method == 'POST':
        theory.swap_titles(user=user)
        theory.update_activity_logs(user, verb='Swapped T/F Titles')
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


# *******************************************************************************
# Opinion views
# *******************************************************************************


def OpinionIndexView(request, content_pk, stats_slug='all'):
    """Index view for opinions.

    Args:
        request ([type]): The post request data.
        pk (int): The theory key.
        stats_slug (str, optional): The category of opinion. Defaults to 'all'.
    """

    # Params
    params = Parameters(request)

    # Setup
    theory = get_object_or_404(Content, pk=content_pk)
    stats_type = Stats.slug_to_type(stats_slug)
    stats = theory.get_stats(stats_type)
    opinions = list(stats.opinions.filter(anonymous=True))
    opinions += list(stats.opinions.filter(anonymous=False).order_by('user__username'))

    # Categories
    categories = {}
    categories['supporters'] = get_or_none(theory.stats, stats_type=Stats.TYPE.SUPPORTERS)
    categories['moderates'] = get_or_none(theory.stats, stats_type=Stats.TYPE.MODERATES)
    categories['opposers'] = get_or_none(theory.stats, stats_type=Stats.TYPE.OPPOSERS)
    categories['all'] = get_or_none(theory.stats, stats_type=Stats.TYPE.ALL)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(opinions, NUM_ITEMS_PER_PAGE * 3)
    opinions = paginator.get_page(page)
    opinions.page_list = get_page_list(paginator.num_pages, page)

    # Render
    context = {
        'theory': theory,
        'stats': stats,
        'opinions': opinions,
        'categories': categories,
        'params': params,
    }
    return render(
        request,
        'theories/opinion_index.html',
        context,
    )


@login_required
def RetrieveMyOpinion(request, content_pk):
    """A method for retrieving and redirecting to edit or view the user's opinion."""

    # Setup
    user = request.user
    theory = get_object_or_404(Content, pk=content_pk)
    opinion = get_or_none(theory.opinions, user=user)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))

    # Redirect
    if opinion is None or opinion.is_deleted():
        return redirect(
            reverse('theories:opinion-my-editor', kwargs={'content_pk': content_pk}) + params)
    else:
        return redirect(opinion.url() + params)


def OpinionDetailView(request, content_pk, opinion_pk=None, opinion_slug=None):
    """The view for displaying opinion and statistical details."""

    # Setup
    user = request.user
    if opinion_pk is not None:
        theory = get_object_or_404(Content, pk=content_pk)
        opinion = get_object_or_404(Opinion, pk=opinion_pk)
        opinion.cache()
    elif opinion_slug is not None:
        if opinion_slug == 'debug':
            opinion = get_demo_opinion()
            theory = opinion.content
        else:
            theory = get_object_or_404(Content, pk=content_pk)
            opinion = theory.get_stats(opinion_slug)
            opinion.cache()
    else:
        raise Http404("Opinion does not exist.")

    # Opinions
    opinions = {}
    if user.is_authenticated:
        opinions['user'] = get_or_none(theory.opinions, user=user)
    opinions['supporters'] = get_or_none(theory.stats, stats_type=Stats.TYPE.SUPPORTERS)
    opinions['moderates'] = get_or_none(theory.stats, stats_type=Stats.TYPE.MODERATES)
    opinions['opposers'] = get_or_none(theory.stats, stats_type=Stats.TYPE.OPPOSERS)
    opinions['all'] = get_or_none(theory.stats, stats_type=Stats.TYPE.ALL)

    # subscribed
    if isinstance(opinion, Opinion):
        subscribed = user.is_authenticated and is_following(user, opinion)
    else:
        subscribed = False

    # Hit counts
    if isinstance(opinion, Opinion):
        opinion.update_hits(request)

    # parent opinions
    parent_opinions = []
    for parent_theory in theory.get_parent_theories():
        if isinstance(opinion, Opinion):
            parent_opinion = get_or_none(parent_theory.opinions, user=opinion.user)
            if parent_opinion is not None and parent_opinion.is_anonymous() == opinion.is_anonymous(
            ):
                parent_opinions.append(parent_opinion)
        elif isinstance(opinion, Stats):
            parent_opinion = get_or_none(parent_theory.stats, stats_type=opinion.stats_type)
            assert parent_opinion is not None
            parent_opinions.append(parent_opinion)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(theory.pk))
    prev = None
    if len(params.path) > 0:
        pk = CONTENT_PK_CYPHER.to_python(params.path[-1])
        parent_theory = get_object_or_404(Content, pk=pk)
        if hasattr(opinion, 'user'):
            parent_opinion = get_or_none(parent_theory.opinions, user=opinion.user)
            if parent_opinion is not None and \
               (parent_opinion.is_anonymous() == opinion.is_anonymous()):
                prev = parent_opinion.url() + params.get_prev()
    compare_url = opinion.compare_url()

    # Flatten
    flat = 'flat' in params.flags
    params00 = params.get_new()
    if flat:
        params00.flags.remove('flat')
    else:
        params00.flags.append('flat')
    swap_flat_url = opinion.url() + params00 + '#VennDiagram'

    # Stats Flag
    stats = 'stats' in params.flags
    params00 = params.get_new()
    if stats:
        params00.flags.remove('stats')
    else:
        params00.flags.append('stats')
    swap_stats_url = opinion.url() + params00

    # Diagrams
    if stats:
        if opinion_slug == 'debug':
            points_diagram = DemoPieChart()
            population_diagram = DemoBarGraph()
        else:
            points_diagram = OpinionPieChart(opinion)
            population_diagram = OpinionBarGraph(opinion)
        evidence_diagram = None
        evidence = None
    else:
        points_diagram = None
        population_diagram = None
        if opinion_slug == 'debug':
            evidence_diagram = DemoVennDiagram()
            evidence = {
                'collaborative': [],
                'controversial': [],
                'contradicting': [],
                'unaccounted': [],
            }
        else:
            evidence_diagram = OpinionVennDiagram(opinion, flat=flat)
            evidence = {
                'collaborative': evidence_diagram.get_collaborative_evidence(sort_list=True),
                'controversial': evidence_diagram.get_controversial_evidence(sort_list=True),
                'contradicting': evidence_diagram.get_contradicting_evidence(sort_list=True),
                'unaccounted': evidence_diagram.get_unaccounted_evidence(sort_list=True),
            }
            for dependency in theory.get_dependencies().exclude(pk=Content.INTUITION_PK):
                if dependency not in evidence['collaborative'] and dependency not in evidence['controversial'] and \
                   dependency not in evidence['contradicting'] and dependency not in evidence['unaccounted']:
                    pass
                    # evidence['unaccounted'].append(dependency)

    # Render
    context = {
        'theory': theory,
        'opinion': opinion,
        'opinions': opinions,
        'subscribed': subscribed,
        'parent_opinions': parent_opinions,
        'evidence': evidence,
        'prev': prev,
        'params': params,
        'flat': flat,
        'stats': stats,
        'swap_flat_url': swap_flat_url,
        'swap_stats_url': swap_stats_url,
        'compare_url': compare_url,
    }
    if evidence_diagram is not None:
        context['evidence_diagram'] = evidence_diagram.get_svg()
        context['evidence_text'] = evidence_diagram.get_caption()
    if points_diagram is not None:
        context['points_diagram'] = points_diagram.get_svg()
        context['points_text'] = points_diagram.get_caption()
    if population_diagram is not None:
        context['population_diagram'] = population_diagram.get_svg()
        context['population_text'] = population_diagram.get_caption()

    return render(
        request,
        'theories/opinion_detail.html',
        context,
    )


def OpinionDemoView(request):
    """A view for demoing the graph visualizations used for opinions."""
    return OpinionDetailView(request, 0, 'debug')


def OpinionCompareView(request,
                       content_pk,
                       opinion_pk01=None,
                       opinion_pk02=None,
                       opinion_slug01=None,
                       opinion_slug02=None):
    """A view for displaying the differences between two opinions."""

    # Setup
    exclude_list = []
    user = request.user
    # Theory
    theory = get_object_or_404(Content, pk=content_pk)
    # Opinion01
    if opinion_pk01 is not None:
        opinion01 = get_object_or_404(Opinion, pk=opinion_pk01)
    elif opinion_slug01 is not None:
        opinion01 = theory.get_stats(opinion_slug01)
    else:
        raise Http404("Opinion does not exist.")
    # Opinion02
    if opinion_pk02 is not None:
        opinion02 = get_object_or_404(Opinion, pk=opinion_pk02)
    elif opinion_slug02 is not None:
        opinion02 = theory.get_stats(opinion_slug02)
    else:
        raise Http404("Opinion does not exist.")
    # Compare list
    compare_list = get_compare_list(opinion01, current_user=user, exclude_list=exclude_list)

    # Navigation
    params = Parameters(request)
    swap_compare_url = opinion02.compare_url(opinion01) + params

    # Flatten
    flat = 'flat' in params.flags
    params00 = params.get_new()
    if flat:
        params00.flags.remove('flat')
    else:
        params00.flags.append('flat')
    swap_flat_url = opinion01.compare_url(opinion02) + params00

    # Diagrams
    points_diagram = OpinionComparisionPieChart(opinion01, opinion02)
    evidence_diagram = OpinionComparisionVennDiagram(opinion01, opinion02, flat=flat)
    population_diagram = OpinionComparisionBarGraph(opinion01, opinion02)
    evidence = {
        'collaborative': evidence_diagram.get_collaborative_evidence(sort_list=True)[:6],
        'controversial': evidence_diagram.get_controversial_evidence(sort_list=True)[:6],
        'contradicting': evidence_diagram.get_contradicting_evidence(sort_list=True)[:6],
        'unaccounted': evidence_diagram.get_unaccounted_evidence(sort_list=True)[:6],
    }

    # Render
    context = {
        'theory': theory,
        'opinion01': opinion01,
        'opinion02': opinion02,
        'compare_list': compare_list,
        'points_diagram': points_diagram.get_svg(),
        'evidence_diagram': evidence_diagram.get_svg(),
        'population_diagram': population_diagram.get_svg(),
        'points_text': points_diagram.get_caption(),
        'evidence_text': evidence_diagram.get_caption(),
        'population_text': population_diagram.get_caption(),
        'evidence': evidence,
        'flat': flat,
        'swap_compare_url': swap_compare_url,
        'swap_flat_url': swap_flat_url,
        'params': params,
    }
    return render(
        request,
        'theories/opinion_compare.html',
        context,
    )


@login_required
def RetrieveMyOpinionEditor(request, content_pk):
    """A method for choosing OpinionAdvEditView or OpinionEditWizardView."""

    # setup
    user = request.user
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))

    # Redirect
    if user.use_wizard:
        return redirect(
            reverse('theories:opinion-wizard', kwargs={'content_pk': content_pk}) + params)
    else:
        return redirect(
            reverse('theories:opinion-edit', kwargs={'content_pk': content_pk}) + params)


@login_required
def OpinionWizardView(request, content_pk):
    return OpinionEditView(request, content_pk, wizard=True)


@login_required
def OpinionEditView(request, content_pk, wizard=False):
    """A view for constructing and editing user opinions."""

    # Setup
    user = request.user
    theory = get_object_or_404(Content, pk=content_pk)
    opinion = get_or_none(theory.opinions, user=user)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(content_pk))
    if opinion is None:
        prev = theory.url() + params
    else:
        prev = opinion.url() + params

    # Setup cont'd
    if opinion is None:
        opinion = Opinion(user=user, content=theory)
        opinion_dependencies = OpinionDependency.objects.none()
        theory_dependencies = theory.get_dependencies()
    else:
        opinion_dependencies = opinion.get_dependencies()
        theory_dependencies = theory.get_dependencies().exclude(
            id__in=opinion_dependencies.values('content'))

    # Formset
    initial = [{'content': x, 'parent': opinion} for x in theory_dependencies]
    OpinionDependencyFormSet = modelformset_factory(OpinionDependency,
                                                    form=OpinionDependencyForm,
                                                    extra=theory_dependencies.count())

    # Post request
    if request.method == 'POST':

        # setup
        opinion_form = OpinionForm(request.POST, instance=opinion, wizard=wizard)
        dependency_formset = OpinionDependencyFormSet(request.POST,
                                                      queryset=opinion_dependencies,
                                                      initial=initial,
                                                      form_kwargs={
                                                          'user': user,
                                                          'wizard': wizard
                                                      })

        # utilization
        utilization_before = {theory: user.is_using(theory)}
        for content in theory_dependencies:
            utilization_before[content] = user.is_using(content)

        # parse
        if opinion_form.is_valid() and dependency_formset.is_valid():

            # remove opinion from stats
            if opinion_form.instance.id is not None:
                theory.remove_from_stats(opinion, cache=True, save=False)

            # save opinion
            if opinion_form.has_changed() or opinion.pk is None:
                opinion = opinion_form.save()

            # save altered dependencies
            for opinion_dependency_form in dependency_formset:
                if opinion_dependency_form.has_changed():
                    opinion_dependency = opinion_dependency_form.save()

            # update points
            opinion.update_points()
            theory.add_to_stats(opinion, cache=True, save=False)
            theory.save_stats()
            opinion.update_activity_logs(user, verb='Modified.')

            # update utilization
            for content in utilization_before.keys():
                utilization_after = content.get_utilization(user)
                if utilization_after and not utilization_before[content]:
                    content.utilization += 1
                elif utilization_before[content] and not utilization_after:
                    content.utilization -= 1

            # done
            return redirect(opinion.url() + params)
        else:
            print(2200, opinion_form.errors)
            print(2201, dependency_formset.errors)

    # Get request
    else:
        opinion_form = OpinionForm(instance=opinion, wizard=wizard)
        dependency_formset = OpinionDependencyFormSet(queryset=opinion_dependencies,
                                                      initial=initial,
                                                      form_kwargs={
                                                          'user': user,
                                                          'wizard': wizard
                                                      })

    # Render
    if wizard:
        template = 'theories/opinion_wizard.html'
    else:
        template = 'theories/opinion_edit.html'
    context = {
        'theory': theory,
        'opinion': opinion,
        'opinion_form': opinion_form,
        'dependency_formset': dependency_formset,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        template,
        context,
    )


@login_required
def OpinionCopy(request, opinion_pk):
    """A method for copying another user's opinion."""

    # Setup
    user = request.user
    opinion = get_object_or_404(Opinion, pk=opinion_pk)
    theory = opinion.content
    recursive = request.POST.get('recursive') == 'yes'

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(opinion_pk))
    prev = opinion.url() + params

    # Post request
    if request.method == 'POST':
        user_opinion = opinion.copy(user, recursive=recursive)
        user_opinion.update_activity_logs(user, verb='Copied', action_object=user_opinion)
        next = user_opinion.url() + params
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


@permission_required('theories.delete_opinion',
                     fn=get_object(Opinion, 'opinion_pk'),
                     raise_exception=True)
def OpinionDelete(request, opinion_pk):
    """A method for deleting the opinion and redirecting the view."""

    # Setup
    user = request.user
    opinion = get_object_or_404(Opinion, pk=opinion_pk)
    theory = opinion.content

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(opinion_pk))
    prev = opinion.url() + params
    next = theory.url() + params

    # Post request
    if request.method == 'POST':
        theory = opinion.content
        opinion.delete()
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


@permission_required('theories.change_opinion',
                     fn=get_object(Opinion, 'opinion_pk'),
                     raise_exception=True)
def OpinionHideUser(request, opinion_pk):
    """A method for hiding the user for the current opinion."""

    # Setup
    user = request.user
    opinion = get_object_or_404(Opinion, pk=opinion_pk)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(opinion_pk))
    prev = request.META.get('HTTP_REFERER', '/')
    next = request.META.get('HTTP_REFERER', '/')

    # Post request
    if request.method == 'POST':
        if not opinion.anonymous:
            opinion.anonymous = True
            opinion.save()
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


@permission_required('theories.change_opinion',
                     fn=get_object(Opinion, 'opinion_pk'),
                     raise_exception=True)
def OpinionRevealUser(request, opinion_pk):
    """A method for revealing the user for the current opinion."""

    # Setup
    user = request.user
    opinion = get_object_or_404(Opinion, pk=opinion_pk)

    # Navigation
    params = Parameters(request, pk=CONTENT_PK_CYPHER.to_url(opinion_pk))
    prev = request.META.get('HTTP_REFERER', '/')
    next = request.META.get('HTTP_REFERER', '/')

    # Post request
    if request.method == 'POST':
        if opinion.anonymous:
            opinion.anonymous = False
            opinion.save()
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


# *******************************************************************************
# Other views
# *******************************************************************************


def ImageView(request, pk=None):
    """The view for displaying opinion and statistical details."""

    # Setup
    user = request.user

    # SVG
    svg = """
      <svg baseProfile="full" version="1.1" viewBox="0 0 755 390" width="453" height="234">
        <rect width="100%" height="100%" fill="white"/>
        <circle cx="250" cy="210" r="150" fill="none" stroke="black" fill-opacity="0.25" stroke-width="4"/>
        <circle cx="505" cy="210" r="150" fill="none" stroke="black" fill-opacity="0.25" stroke-width="4"/>
        <circle cx="154" cy="138" r="25" fill="black" stroke-width="0"/>
        <circle cx="245" cy="180" r="25" fill="black" stroke-width="0"/>
        <circle cx="160" cy="240" r="25" fill="black" stroke-width="0"/>
        <circle cx="132" cy="190" r="25" fill="black" stroke-width="0"/>
        <circle cx="243" cy="320" r="25" fill="black" stroke-width="0"/>
        <circle cx="167" cy="296" r="25" fill="black" stroke-width="0"/>
        <rect x="277" y="241" width="20" height="20" fill="black" fill-opacity="1.00" stroke-width="0"/>
        <rect x="188" y="319" width="20" height="20" fill="black" fill-opacity="1.00" stroke-width="0"/>
        <text text-anchor="middle" x="250" y="47" font-size="40" font-family="FreeSerif" font-weight="bold" fill="black">True</text>
        <text text-anchor="middle" x="505" y="47" font-size="40" font-family="FreeSerif" font-weight="bold" fill="red">False</text>
      </svg>
    """
    #    svg2png(bytestring=svg, write_to='output.png')
    image = open("output.png", "rb").read()
    return HttpResponse(image, content_type="image/png")
