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

from theories.models import Category, TheoryNode, Opinion, OpinionNode, Stats
from theories.forms import TheoryForm, EvidenceForm, OpinionForm
from theories.forms import SelectTheoryNodeForm, OpinionNodeForm
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
#
#
#
#
#
#
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
                'url': reverse('theories:get_my_opinion', kwargs={'pk': theory.pk}),
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
    theory = opinion01.theory
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
# Theory views
#
#
#
#
#
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


def TheoryIndexView(request, cat=None):
    """Home view for display all root theories."""

    # Setup
    user = request.user

    # Categories
    if cat is None:
        category = get_object_or_404(Category, title='All')
    else:
        category = get_object_or_404(Category, slug=cat)
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


def ActivityView(request, cat=None):
    """Home view for display all root theories."""

    # Setup
    user = request.user
    date = request.GET.get('date', None)

    # Category
    if cat is None:
        category = get_object_or_404(Category, slug='all')
    else:
        category = get_object_or_404(Category, slug=cat)
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


class TheoryDetail(generic.DetailView):
    """A view for displaying theory details."""
    model = TheoryNode
    template_name = 'theories/theory_detail.html'
    TheoryNode.update_intuition_node()

    def get_context_data(self, **kwargs):

        # Setup
        theory = self.object
        deleted = theory.is_deleted()
        parent_theories = theory.get_parent_nodes(deleted=deleted)
        theory_nodes = theory.get_nodes(deleted=deleted).exclude(pk=TheoryNode.INTUITION_PK)

        opinions = {}
        opinions['supporters'] = get_or_none(theory.stats, stats_type=Stats.TYPE.SUPPORTERS)
        opinions['moderates'] = get_or_none(theory.stats, stats_type=Stats.TYPE.MODERATES)
        opinions['opposers'] = get_or_none(theory.stats, stats_type=Stats.TYPE.OPPOSERS)
        opinions['all'] = get_or_none(theory.stats, stats_type=Stats.TYPE.ALL)

        # Pagination
        page = self.request.GET.get('page')
        paginator = Paginator(theory_nodes, NUM_ITEMS_PER_PAGE)
        theory_nodes = paginator.get_page(page)
        theory_nodes.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

        # Navigation
        params = Parameters(self.request, pk=theory.pk)
        if len(params.path) > 0:
            parent_theory = get_object_or_404(TheoryNode, pk=params.path[-1])
            prev = parent_theory.url() + params.get_prev()
        else:
            prev = reverse('theories:index') + params

        # Hit counts
        theory.update_hits(self.request)

        # Context
        context = {
            'theory': theory,
            'theory_nodes': theory_nodes,
            'parent_theories': parent_theories,
            'opinions': opinions,
            'prev': prev,
            'params': params,
        }
        return context


def OpinionIndexView(request, pk, slug):
    """Index view for opinions.

    Args:
        request ([type]): The post request data.
        pk (int): The theory key.
        slug (str, optional): The category of opinion. Defaults to 'all'.
    """

    # Params
    params = Parameters(request)

    # Setup
    theory = get_object_or_404(TheoryNode, pk=pk)
    stats_type = Stats.slug_to_type(slug)
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
@permission_required('theories.add_theorynode', raise_exception=True)
def TheoryCreateView(request, cat):
    """View for create a new theory."""

    # Setup
    user = request.user
    category = get_object_or_404(Category, slug=cat)

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
@permission_required('theories.change_theorynode',
                     fn=get_object(TheoryNode, 'pk'),
                     raise_exception=True)
def TheoryEditView(request, pk):
    """A view for editing theory details."""

    # Setup
    user = request.user
    theory = get_object_or_404(TheoryNode, pk=pk)

    # Navigation
    params = Parameters(request, pk=pk)
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        root_theory = get_object_or_404(TheoryNode, pk=params.path[0])
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
@permission_required('theories.add_theorynode', raise_exception=True)
def TheoryEditEvidenceView(request, pk):
    """A view for editing evidence details for the pertaining theory."""

    # Setup
    user = request.user
    theory = get_object_or_404(TheoryNode, pk=pk)
    evidence_nodes = theory.get_evidence_nodes()
    EvidenceFormSet = modelformset_factory(TheoryNode, form=EvidenceForm, extra=3)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(evidence_nodes, NUM_ITEMS_PER_PAGE)
    evidence_nodes = paginator.get_page(page)
    evidence_nodes.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request, pk=pk)
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        root_theory = get_object_or_404(TheoryNode, pk=params.path[0])
    else:
        root_theory = theory

    # Post request
    if request.method == 'POST':
        formset = EvidenceFormSet(request.POST,
                                  queryset=evidence_nodes.object_list,
                                  form_kwargs={'user': user})
        if formset.is_valid():
            for form in formset:
                if form.has_changed():
                    # save
                    evidence = form.save()
                    # update nodes
                    theory.add_node(evidence)
                    # activity log
                    evidence.update_activity_logs(user, form.get_verb())
            return redirect(prev)
        else:
            print(238, formset.errors)

    # Get request
    else:
        formset = EvidenceFormSet(queryset=evidence_nodes.object_list, form_kwargs={'user': user})

    # Render
    context = {
        'root_theory': root_theory,
        'theory': theory,
        'formset': formset,
        'evidence_nodes': evidence_nodes,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/theory_edit_evidence.html',
        context,
    )


@login_required
@permission_required('theories.add_theorynode', raise_exception=True)
def TheoryEditSubtheoriesView(request, pk):
    """A view for editing sub-theory details for the pertaining theory."""

    # Setup
    user = request.user
    theory = get_object_or_404(TheoryNode, pk=pk)
    subtheory_nodes = theory.get_subtheory_nodes()
    SubTheoryFormSet = modelformset_factory(TheoryNode, form=TheoryForm, extra=3)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(subtheory_nodes, NUM_ITEMS_PER_PAGE)
    subtheory_nodes = paginator.get_page(page)
    subtheory_nodes.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request, pk=pk)
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        root_theory = get_object_or_404(TheoryNode, pk=params.path[0])
    else:
        root_theory = theory

    # Post request
    if request.method == 'POST':
        formset = SubTheoryFormSet(request.POST,
                                   queryset=subtheory_nodes.object_list,
                                   form_kwargs={'user': user})
        if formset.is_valid():
            for form in formset:
                if form.has_changed():
                    # save
                    subtheory = form.save()
                    # update nodes
                    theory.add_node(subtheory)
                    # activity log
                    subtheory.update_activity_logs(user, verb=form.get_verb())
            return redirect(next)
        else:
            print(220, formset.errors)

    # Get request
    else:
        formset = SubTheoryFormSet(queryset=subtheory_nodes.object_list, form_kwargs={'user': user})

    # Render
    context = {
        'root_theory': root_theory,
        'theory': theory,
        'formset': formset,
        'subtheory_nodes': subtheory_nodes,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        'theories/theory_edit_subtheories.html',
        context,
    )


@login_required
@permission_required('theories.merge_theorynode',
                     fn=get_object(TheoryNode, 'pk'),
                     raise_exception=True)
def TheoryMergeView(request, pk):
    """A view for merging theories."""

    # Setup
    user = request.user
    theory = get_object_or_404(TheoryNode, pk=pk)

    # Navigation
    params = Parameters(request, pk=pk)
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        parent_theory = get_object_or_404(TheoryNode, pk=params.path[-1])
        root_theory = get_object_or_404(TheoryNode, pk=params.path[0])
    else:
        parent_theory = theory
        root_theory = theory

    # Setup cont'd
    candidates = parent_theory.get_nested_subtheory_nodes().filter(
        node_type=theory.node_type).exclude(pk=theory.pk)
    MergeFormSet = modelformset_factory(TheoryNode, form=SelectTheoryNodeForm, extra=0)

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
                    theory_node = form.instance
                    # merge
                    theory.merge(theory_node, user=user)
                    # activity log
                    theory.update_activity_logs(user,
                                                verb='Merged with <# object.url {{ object }} #>',
                                                action_object=theory_node)
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
def TheoryInheritView(request, pk01, pk02):
    """A view for inheriting evidence/sub-theories into the pertaining theory."""

    # Setup
    user = request.user
    theory = get_object_or_404(TheoryNode, pk=pk01)
    root_theory = get_object_or_404(TheoryNode, pk=pk02)

    # Navigation
    params = Parameters(request, pk=pk01)
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    path_theory_pks = params.path + [theory.pk]
    root_nodes = root_theory.get_nested_nodes().exclude(pk=TheoryNode.INTUITION_PK)
    root_nodes = root_nodes | TheoryNode.objects.filter(pk=root_theory.pk)
    candidates = root_nodes.exclude(pk__in=theory.get_nodes())
    candidates = candidates.exclude(pk__in=path_theory_pks)
    exclude_other = root_nodes.values_list('pk', flat=True)
    other_theories = Category.get('All').get_theories().exclude(pk__in=exclude_other)
    InheritFormSet = modelformset_factory(TheoryNode, form=SelectTheoryNodeForm, extra=0)

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
                    node = form.instance
                    # inherit
                    theory.add_node(node)
                    # activity log
                    theory.update_activity_logs(user,
                                                verb='Inherited <# object.url {{ object }} #>',
                                                action_object=node)
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
@permission_required('theories.change_theorynode', raise_exception=True)
def TheoryRestoreView(request, pk):
    """A view for reviewing/deleting theory revisions."""

    # Setup
    user = request.user
    theory = get_object_or_404(TheoryNode, pk=pk)
    revisions = theory.get_revisions()
    RevisionFormSet = modelformset_factory(Version, form=TheoryRevisionForm, extra=0)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(revisions, NUM_ITEMS_PER_PAGE)
    revisions = paginator.get_page(page)
    revisions.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request, pk=pk)
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        root_theory = get_object_or_404(TheoryNode, pk=params.path[0])
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
@permission_required('theories.backup_theorynode', raise_exception=True)
def TheoryBackupView(request, pk):
    """A method for taking a snap-shot (backup) of a theory node."""

    # Setup
    user = request.user
    theory = get_object_or_404(TheoryNode, pk=pk)
    candidates = TheoryNode.objects.filter(pk=theory.pk) | theory.get_nested_nodes()
    candidates = candidates.exclude(pk=TheoryNode.INTUITION_PK)
    BackupFormSet = modelformset_factory(TheoryNode, form=SelectTheoryNodeForm, extra=0)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(candidates, NUM_ITEMS_PER_PAGE * 4)
    candidates = paginator.get_page(page)
    candidates.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request, pk=pk)
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        root_theory = get_object_or_404(TheoryNode, pk=params.path[0])
    else:
        root_theory = theory

    # Post request
    if request.method == 'POST':
        formset = BackupFormSet(request.POST, queryset=candidates.object_list)
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data['select']:
                    theory_node = form.instance
                    theory_node.save_snapshot(user)
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


def TheoryReportView(request, pk):

    # Setup
    user = request.user
    theory = get_object_or_404(TheoryNode, pk=pk)
    open_violations = theory.get_violations(opened=True, closed=False)
    closed_violations = theory.get_violations(opened=False, closed=True)

    # Navigation
    params = Parameters(request, pk=pk)
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        root_theory = get_object_or_404(TheoryNode, pk=params.path[0])
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


def EvidenceReportView(request, pk):

    # Setup
    user = request.user
    evidence = get_object_or_404(TheoryNode, pk=pk)

    # Navigation
    params = Parameters(request, pk=pk)
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


def TheoryActivityView(request, pk):
    """A view for theory activity."""

    # Setup
    user = request.user
    date = request.GET.get('date', None)
    theory = get_object_or_404(TheoryNode, pk=pk)
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
    params = Parameters(request, pk=pk)
    prev = theory.url() + params
    next = theory.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        root_theory = get_object_or_404(TheoryNode, pk=params.path[0])
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
#
#
#
#
#
# *******************************************************************************


class EvidenceDetail(generic.DetailView):
    """A view for displaying evidence details."""
    model = TheoryNode
    template_name = 'theories/evidence_detail.html'

    def get_context_data(self, **kwargs):

        # Setup
        evidence = self.object
        parent_theories = evidence.get_parent_nodes()

        # Navigation
        params = Parameters(self.request, pk=evidence.pk)
        if len(params.path) > 0:
            parent_theory = get_object_or_404(TheoryNode, pk=params.path[-1])
            prev = parent_theory.url() + params.get_prev()
        else:
            prev = reverse('theories:index') + params

        # Hit counts
        evidence.update_hits(self.request)

        # Context
        context = {
            'parent_theories': parent_theories,
            'evidence': evidence,
            'prev': prev,
            'params': params,
        }
        return context


@login_required
@permission_required('theories.change_theorynode',
                     fn=get_object(TheoryNode, 'pk'),
                     raise_exception=True)
def EvidenceEditView(request, pk):
    """A view for editing evidence details."""

    # Setup
    user = request.user
    evidence = get_object_or_404(TheoryNode, pk=pk)

    # Navigation
    params = Parameters(request, pk=pk)
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
@permission_required('theories.merge_theorynode',
                     fn=get_object(TheoryNode, 'pk'),
                     raise_exception=True)
def EvidenceMergeView(request, pk):
    """A view for merging theories."""

    # Setup
    user = request.user
    evidence = get_object_or_404(TheoryNode, pk=pk)

    # Navigation
    params = Parameters(request, pk=pk)
    prev = evidence.url() + params
    next = evidence.url() + params

    # Setup cont'd
    if len(params.path) > 0:
        parent_theory = get_object_or_404(TheoryNode, pk=params.path[-1])
    else:
        return redirect('theories:index')

    # Setup cont'd
    candidates = parent_theory.get_flat_nodes().filter(node_type=evidence.node_type)
    candidates = candidates.exclude(pk=evidence.pk).exclude(pk=TheoryNode.INTUITION_PK)
    MergeFormSet = modelformset_factory(TheoryNode, form=SelectTheoryNodeForm, extra=0)

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
                    theory_node = form.instance
                    # merge
                    evidence.merge(theory_node, user=user)
                    # activity log
                    evidence.update_activity_logs(user, verb='Merge', action_object=theory_node)
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
@permission_required('theories.change_theorynode', raise_exception=True)
def EvidenceRestoreView(request, pk):
    """A view for reviewing evidence revisions."""

    # Setup
    user = request.user
    evidence = get_object_or_404(TheoryNode, pk=pk)
    revisions = evidence.get_revisions()
    RevisionFormSet = modelformset_factory(Version, form=EvidenceRevisionForm, extra=0)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(revisions, NUM_ITEMS_PER_PAGE)
    revisions = paginator.get_page(page)
    revisions.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request, pk=pk)
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


def EvidenceActivityView(request, pk):
    """A view for evidence activity."""

    # Setup
    user = request.user
    date = request.GET.get('date', None)
    evidence = get_object_or_404(TheoryNode, pk=pk)
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
    params = Parameters(request, pk=pk)
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
# Methods
#
#
#
#
#
# *******************************************************************************


@permission_required('theories.delete_edge', fn=get_object(TheoryNode, 'pk'), raise_exception=True)
def TheoryNodeRemove(request, pk):
    """A redirect for deleting theory node edges (removing from parents)."""

    # Setup
    user = request.user
    theory_node = get_object_or_404(TheoryNode, pk=pk)

    # Navigation
    params = Parameters(request, pk=pk)
    prev = theory_node.url() + params
    if len(params.path) > 0:
        parent_theory = get_object_or_404(TheoryNode, pk=params.path[-1])
        next = parent_theory.url() + params.get_prev()
    else:
        return reverse('theories:index')

    # Post request
    if request.method == 'POST':
        parent_theory.remove_node(theory_node, user)
        parent_theory.update_activity_logs(user,
                                           verb='Removed <# object.url {{ object }} #>',
                                           action_object=theory_node)
        # cleanup abandoned theory
        if theory_node.parent_nodes.count() == 0 and not theory_node.is_root():
            theory_node.delete(user)
            theory_node.update_activity_logs(user, verb='Deleted.')
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


@permission_required('theories.delete_theorynode',
                     fn=get_object(TheoryNode, 'pk'),
                     raise_exception=True)
def TheoryNodeDelete(request, pk):
    """A redirect for deleting theory nodes."""

    # Setup
    user = request.user
    theory_node = get_object_or_404(TheoryNode, pk=pk)

    # Navigation
    params = Parameters(request, pk=pk)
    prev = theory_node.url() + params
    if len(params.path) > 0:
        parent_theory = get_object_or_404(TheoryNode, pk=params.path[-1])
        next = parent_theory.url() + params.get_prev()
    else:
        parent_theory = None
        next = reverse('theories:index') + params

    # Post request
    if request.method == 'POST':
        theory_node.delete(user)
        theory_node.update_activity_logs(user, verb='Deleted')
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


@login_required
@permission_required('theories.backup_theorynode', raise_exception=True)
def BackupTheoryNode(request, pk):
    """A method for taking a snap-shot (backup) of a theory node."""

    # Setup
    user = request.user
    theory_node = get_object_or_404(TheoryNode, pk=pk)

    # Navigation
    params = Parameters(request, pk=pk)
    prev = request.META.get('HTTP_REFERER', '/')
    next = request.META.get('HTTP_REFERER', '/')

    # Post request
    if request.method == 'POST':
        theory_node.save_snapshot(user)
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


@permission_required('theories.restore_theorynode',
                     fn=get_object(TheoryNode, 'pk'),
                     raise_exception=True)
def RevertTheoryNode(request, pk, vid):
    """A method for restoring a theory-node snap-shot (backup)."""

    # Setup
    user = request.user
    theory_node = get_object_or_404(TheoryNode, pk=pk)
    version = get_object_or_404(Version, id=vid)

    # Navigation
    params = Parameters(request, pk=pk)
    prev = request.META.get('HTTP_REFERER', '/')
    next = theory_node.url() + params

    # Post request
    if request.method == 'POST':
        with reversion.create_revision():
            theory_node.save()
            reversion.set_user(theory_node.modified_by)
            reversion.set_comment('AutoSave - Revert')
        for key in version.field_dict.keys():
            setattr(theory_node, key, version.field_dict[key])
        theory_node.save()
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


@permission_required('theories.convert_theorynode',
                     fn=get_object(TheoryNode, 'pk'),
                     raise_exception=True)
def TheoryNodeConvert(request, pk):
    """A method for converting a sub-theories to evidence and vise-a-versa."""

    # Setup
    user = request.user
    theory_node = get_object_or_404(TheoryNode, pk=pk)
    verifiable = request.POST.get('verifiable') in ['True', 'yes']

    # Navigation
    params = Parameters(request, pk=pk)
    prev = theory_node.url() + params
    if len(params.path) == 0:
        if theory_node.is_root() or theory_node.is_evidence():
            return redirect('theories:index')
    else:
        parent_theory = get_object_or_404(TheoryNode, pk=params.path[-1])

    # Post request
    if request.method == 'POST':
        # convert
        theory_node.convert(user, verifiable=verifiable)
        # activity
        if theory_node.is_evidence():
            theory_node.update_activity_logs(user, verb='Converted to Evidence')
        else:
            theory_node.update_activity_logs(user, verb='Converted to Sub-Theory')
        next = theory_node.url() + params
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


@permission_required('theories.swap_title', fn=get_object(TheoryNode, 'pk'), raise_exception=True)
def TheorySwapTitles(request, pk):
    """A redirect for swapping the theory true/false statements."""

    # Setup
    user = request.user
    theory = get_object_or_404(TheoryNode, pk=pk)

    # Navigation
    params = Parameters(request, pk=pk)
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


@login_required
@permission_required('theories.change_theorynode',
                     fn=get_object(TheoryNode, 'pk'),
                     raise_exception=True)
def TheoryAddToHome(request, pk):
    """A redirect for adding the theory to the 'All' category, which in turn
       will allow it to be displayed on the home page."""

    # Setup
    user = request.user
    theory = get_object_or_404(TheoryNode, pk=pk)

    # Navigation
    params = Parameters(request, pk=pk)
    prev = request.META.get('HTTP_REFERER', '/')
    next = request.META.get('HTTP_REFERER', '/')

    # Post request
    if request.method == 'POST':
        category_all = get_object_or_404(Category, slug='all')
        theory.categories.add(category_all)
        action.send(user, verb='Added', action_object=theory, target=category_all)
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


@login_required
@permission_required('theories.change_theorynode',
                     fn=get_object(TheoryNode, 'pk'),
                     raise_exception=True)
def TheoryRemoveFromHome(request, pk):
    """A redirect for removing the theory form the 'All' category, which in turn
       will remove it from the home page."""

    # Setup
    user = request.user
    theory = get_object_or_404(TheoryNode, pk=pk)

    # Navigation
    params = Parameters(request, pk=pk)
    prev = request.META.get('HTTP_REFERER', '/')
    next = request.META.get('HTTP_REFERER', '/')

    # Post request
    if request.method == 'POST':
        for category in theory.categories.all():
            action.send(user, verb='Removed', action_object=theory, target=category)
        theory.categories.clear()
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


# *******************************************************************************
# Opinion views
#
#
#
#
#
# *******************************************************************************


@login_required
def RetrieveMyOpinion(request, pk):
    """A method for retrieving and redirecting to edit or view the user's opinion."""

    # Setup
    user = request.user
    theory = get_object_or_404(TheoryNode, pk=pk)
    opinion = get_or_none(theory.opinions, user=user)

    # Navigation
    params = Parameters(request, pk=pk)

    # Redirect
    if opinion is None or opinion.is_deleted():
        return redirect(reverse('theories:opinion-my-editor', kwargs={'pk': pk}) + params)
    else:
        return redirect(opinion.url() + params)


def OpinionDetailView(request, pk, slug):
    """The view for displaying opinion and statistical details."""

    # Setup
    user = request.user
    if slug == 'debug':
        opinion = get_demo_opinion()
        theory = opinion.theory
    elif re.match(r'^\d+$', slug):
        theory = get_object_or_404(TheoryNode, pk=pk)
        opinion = get_object_or_404(Opinion, pk=int(slug))
        opinion.cache()
    else:
        theory = get_object_or_404(TheoryNode, pk=pk)
        opinion = theory.get_stats(slug)
        opinion.cache()

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
    for parent_theory in theory.get_parent_nodes():
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
    params = Parameters(request, pk=theory.pk)
    prev = None
    if len(params.path) > 0:
        parent_theory = get_object_or_404(TheoryNode, pk=params.path[-1])
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
        if slug == 'debug':
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
        if slug == 'debug':
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
            for node in theory.get_nodes().exclude(pk=TheoryNode.INTUITION_PK):
                if node not in evidence['collaborative'] and node not in evidence['controversial'] and \
                   node not in evidence['contradicting'] and node not in evidence['unaccounted']:
                    pass
                    # evidence['unaccounted'].append(node)

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


def OpinionCompareView(request, pk, slug01, slug02):
    """A view for displaying the differences between two opinions."""

    # Setup
    user = request.user
    # Opinion01
    if re.match(r'^\d+$', slug01):
        opinion01 = get_object_or_404(Opinion, pk=int(slug01))
    else:
        opinion01 = theory.get_stats(slug01)
    # Opinion02
    if re.match(r'^\d+$', slug02):
        opinion02 = get_object_or_404(Opinion, pk=int(slug02))
    else:
        opinion02 = theory.get_stats(slug02)
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
def RetrieveMyOpinionEditor(request, pk):
    """A method for choosing OpinionAdvEditView or OpinionEditWizardView."""

    # setup
    user = request.user
    params = Parameters(request, pk=pk)

    # Redirect
    if user.use_wizard:
        return redirect(reverse('theories:opinion-wizard', kwargs={'pk': pk}) + params)
    else:
        return redirect(reverse('theories:opinion-edit', kwargs={'pk': pk}) + params)


@login_required
def OpinionWizardView(request, pk):
    return OpinionEditView(request, pk, wizard=True)


@login_required
def OpinionEditView(request, pk, wizard=False):
    """A view for constructing and editing user opinions."""

    # Setup
    user = request.user
    theory = get_object_or_404(TheoryNode, pk=pk)
    opinion = get_or_none(theory.opinions, user=user)

    # Navigation
    params = Parameters(request, pk=pk)
    if opinion is None:
        prev = theory.url() + params
    else:
        prev = opinion.url() + params

    # Setup cont'd
    if opinion is None:
        opinion = Opinion(user=user, theory=theory)
        opinion_nodes = OpinionNode.objects.none()
        theory_nodes = theory.get_nodes()
    else:
        opinion_nodes = opinion.get_nodes()
        theory_nodes = theory.get_nodes().exclude(id__in=opinion_nodes.values('theory_node'))

    # Formset
    initial = [{'theory_node': x, 'parent': opinion} for x in theory_nodes]
    OpinionNodeFormSet = modelformset_factory(OpinionNode,
                                              form=OpinionNodeForm,
                                              extra=theory_nodes.count())

    # Post request
    if request.method == 'POST':

        # setup
        opinion_form = OpinionForm(request.POST, instance=opinion, wizard=wizard)
        node_formset = OpinionNodeFormSet(request.POST,
                                          queryset=opinion_nodes,
                                          initial=initial,
                                          form_kwargs={
                                              'user': user,
                                              'wizard': wizard
                                          })

        # utilization
        utilization_before = {theory: user.is_using(theory)}
        for theory_node in theory_nodes:
            utilization_before[theory_node] = user.is_using(theory_node)

        # parse
        if opinion_form.is_valid() and node_formset.is_valid():

            # remove opinion from stats
            if opinion_form.instance.id is not None:
                theory.remove_from_stats(opinion, cache=True, save=False)

            # save opinion
            if opinion_form.has_changed() or opinion.pk is None:
                opinion = opinion_form.save()

            # save altered dependencies
            for opinion_node_form in node_formset:
                if opinion_node_form.has_changed():
                    opinion_node = opinion_node_form.save()

            # update points
            opinion.update_points()
            theory.add_to_stats(opinion, cache=True, save=False)
            theory.save_stats()
            opinion.update_activity_logs(user, verb='Modified.')

            # update utilization
            for theory_node in utilization_before.keys():
                utilization_after = theory_node.get_utilization(user)
                if utilization_after and not utilization_before[theory_node]:
                    theory_node.utilization += 1
                elif utilization_before[theory_node] and not utilization_after:
                    theory_node.utilization -= 1

            # done
            return redirect(opinion.url() + params)
        else:
            print(2200, opinion_form.errors)
            print(2201, node_formset.errors)

    # Get request
    else:
        opinion_form = OpinionForm(instance=opinion, wizard=wizard)
        node_formset = OpinionNodeFormSet(queryset=opinion_nodes,
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
        'node_formset': node_formset,
        'prev': prev,
        'params': params,
    }
    return render(
        request,
        template,
        context,
    )


@login_required
def OpinionCopy(request, pk):
    """A method for copying another user's opinion."""

    # Setup
    user = request.user
    opinion = get_object_or_404(Opinion, pk=pk)
    theory = opinion.theory
    recursive = request.POST.get('recursive') == 'yes'

    # Navigation
    params = Parameters(request, pk=pk)
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


@permission_required('theories.delete_opinion', fn=get_object(Opinion, 'pk'), raise_exception=True)
def OpinionDelete(request, pk):
    """A method for deleting the opinion and redirecting the view."""

    # Setup
    user = request.user
    opinion = get_object_or_404(Opinion, pk=pk)
    theory = opinion.theory

    # Navigation
    params = Parameters(request, pk=pk)
    prev = opinion.url() + params
    next = theory.url() + params

    # Post request
    if request.method == 'POST':
        theory = opinion.theory
        opinion.delete()
        return redirect(next)

    # Get request
    else:
        return redirect(prev)


@permission_required('theories.change_opinion', fn=get_object(Opinion, 'pk'), raise_exception=True)
def OpinionHideUser(request, pk):
    """A method for hiding the user for the current opinion."""

    # Setup
    user = request.user
    opinion = get_object_or_404(Opinion, pk=pk)

    # Navigation
    params = Parameters(request, pk=pk)
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


@permission_required('theories.change_opinion', fn=get_object(Opinion, 'pk'), raise_exception=True)
def OpinionRevealUser(request, pk):
    """A method for revealing the user for the current opinion."""

    # Setup
    user = request.user
    opinion = get_object_or_404(Opinion, pk=pk)

    # Navigation
    params = Parameters(request, pk=pk)
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
