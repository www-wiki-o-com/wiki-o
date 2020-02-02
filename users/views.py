"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       users/views.py
@brief      A collection of app specific views
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# imports
# *******************************************************************************
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse, reverse_lazy
from django.shortcuts import render
from django.views import generic
from django.core.paginator import Paginator
from django.forms import Textarea, modelformset_factory
from actstream.models import user_stream, target_stream, following, followers
from notifications.models import Notification
from reversion.models import Version

from .models import *
from .forms import *
from theories.forms import *
from theories.models import Category, TheoryNode, Opinion
from theories.views import get_page_list, MAX_NUM_PAGES, NUM_ITEMS_PER_PAGE, Parameters


# *******************************************************************************
# methods
# *******************************************************************************


# *******************************************************************************
# classes
# *******************************************************************************


# ************************************************************
#
# ************************************************************
def PublicProfileView(request, pk):
    # Setup
    user = get_object_or_404(User, pk=pk)
    current_user = request.user
    if user.hidden:
        public_opinions = Opinion.objects.none()
        private_opinions = user.opinions.all()
    else:
        public_opinions = user.opinions.filter(anonymous=False)
        private_opinions = user.opinions.filter(anonymous=True)

    # Navigation
    parms = Parameters(request)
    prev = request.META.get('HTTP_REFERER', '/')
    next = request.META.get('HTTP_REFERER', '/')

    # RENDER
    context = {
        'user':                 user,
        'current_user':         current_user,
        'public_opinions':      public_opinions,
        'private_opinions':     private_opinions,
        'num_soft_strikes':     user.count_strikes(recent=True, expired=False, soft=True, hard=False),
        'num_hard_strikes':     user.count_strikes(recent=True, expired=False, soft=False, hard=True),
        'num_expired_strikes':  user.count_strikes(recent=False, expired=True),
        'num_total_strikes':    user.count_strikes(recent=True, expired=True),
        'prev':                 prev,
        'parms':                parms,
    }
    return render(
        request,
        'users/user_detail.html',
        context,
    )


# ************************************************************
#
# ************************************************************
@login_required
def PrivateProfileView(request):

    # Setup
    user = request.user

    # Navigation
    prev = reverse('users:profile-detail', kwargs={'pk': user.id})
    next = reverse('users:profile-detail', kwargs={'pk': user.id})

    # POST request
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid() and form.has_changed():
            form.save()
            return redirect(next)
        else:
            print(100, form.errors)

    # GET request
    else:
        form = UserForm(instance=user)

    # RENDER
    context = {
        'form':   form,
        'prev':   prev,
    }
    return render(
        request,
        'users/user_edit_form.html',
        context,
    )


# ************************************************************
# ToDo: double pagination
# ************************************************************
@login_required
def NotificationsView(request):

    # Setup
    user = request.user
    opinions = following(user, Opinion)
    theories = following(user, TheoryNode)
    categories = following(user, Category)
    notifications = user.notifications.all()
    user_violations = user.violations.all()
    NotificationFormset = modelformset_factory(
        Notification, form=SelectNotificationForm, extra=0)
    ViolationFormset = modelformset_factory(
        Violation, form=SelectViolationForm, extra=0)

    # Pagination01
    page01 = request.GET.get('page01')
    paginator01 = Paginator(notifications, NUM_ITEMS_PER_PAGE)
    notifications = paginator01.get_page(page01)
    notifications.page_list = get_page_list(paginator01.num_pages, page01)
    # Pagination02
    page02 = request.GET.get('page02')
    paginator02 = Paginator(user_violations, NUM_ITEMS_PER_PAGE)
    user_violations = paginator02.get_page(page02)
    user_violations.page_list = get_page_list(paginator02.num_pages, page02)

    # Navigation
    prev = request.META.get('HTTP_REFERER', '/')
    next = request.META.get('HTTP_REFERER', '/')

    # POST request
    if request.method == 'POST':
        action = request.POST.get('action')
        formset01 = NotificationFormset(
            request.POST, queryset=notifications.object_list, prefix='notifications')
        formset02 = ViolationFormset(
            request.POST, queryset=user_violations.object_list, prefix='feedback')
        if formset01.is_valid() and formset02.is_valid():
            if action == 'Mark as Read':
                for form in formset01:
                    if form.cleaned_data['select']:
                        form.instance.mark_as_read()
                for form in formset02:
                    if form.cleaned_data['select']:
                        form.instance.mark_as_read()
            elif action == 'Mark as Un-Read':
                for form in formset01:
                    if form.cleaned_data['select']:
                        form.instance.mark_as_unread()
                for form in formset02:
                    if form.cleaned_data['select']:
                        form.instance.mark_as_unread()
            elif action == 'Delete':
                for form in formset01:
                    if form.cleaned_data['select']:
                        form.instance.delete()
            return redirect(next)
        else:
            print(140, formset01.errors)
            print(142, formset02.errors)

    # GET request
    else:
        formset01 = NotificationFormset(
            queryset=notifications.object_list, prefix='notifications')
        formset02 = ViolationFormset(
            queryset=user_violations.object_list, prefix='feedback')

    # RENDER
    context = {
        'notifications':            notifications,
        'user_violations':          user_violations,
        'opinions':                 opinions,
        'theories':                 theories,
        'categories':               categories,
        'formset01':                formset01,
        'formset02':                formset02,
    }
    return render(
        request,
        'users/user_notifications.html',
        context,
    )


# ************************************************************
#
# ************************************************************
def ViolationIndexView(request):

    # Setup
    user = request.user
    date = request.GET.get('date', None)
    violations = Violation.objects.all()

    # Violations
    if date is not None:
        date = unquote(date)
        violations = violations.filter(modified_date__gte=date)

    # Search
    search_term = request.GET.get('search', '')
    if len(search_term) > 0:
        print(220, search_term)
        violations = violations.filter(
            offender__username__icontains=search_term)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(violations, NUM_ITEMS_PER_PAGE)
    violations = paginator.get_page(page)
    violations.page_list = get_page_list(paginator.num_pages, page)

    # Navigation
    parms = Parameters(request)

    # Render
    context = {
        'violations':           violations,
        'date_filter':          date,
        'parms':                parms,
    }
    return render(
        request,
        'users/violation_index.html',
        context,
    )


# ************************************************************
# ToDo: add get_violations to user to filter active violations as well as warnings and accepted
# ************************************************************
def ViolationResolveView(request, pk):

    # Setup
    user = request.user
    violation = get_object_or_404(Violation, pk=pk)
    related_violations = violation.content.violations.exclude(pk=pk)
    user_violations = violation.offender.violations.exclude(pk=pk)
    vote = get_first_or_none(violation.votes.all(), user=user)
    if vote is None:
        vote = ViolationVote(violation=violation, user=user)

    # content - theory_node
    content_type = violation.content_type.model
    if content_type == 'theorynode':
        theory_node = violation.content
        revisions = theory_node.get_revisions().filter(
            revision__date_created__date__lte=violation.pub_date)
        RevisionFormSet = modelformset_factory(
            Version, form=TheoryRevisionForm, extra=0)
        revision_formset = RevisionFormSet(queryset=revisions, form_kwargs={
                                           'user': user, 'hide_delete': True})
    else:
        theory_node = None
        revision_formset = []

    # Navigation
    parms = Parameters(request)
    prev = reverse('users:violations') + parms
    next = reverse('users:violation-resolve', kwargs={'pk': pk}) + parms

    # POST request
    if request.method == 'POST':

        # debug
        print('\n\n\n')
        print(request.POST)
        print('\n\n\n')

        # vote
        vote_form = VoteForm(request.POST, instance=vote,
                             violation=violation, user=user, prefix='vote')
        if 'save_vote' in request.POST.keys() and user.has_perm('users.can_vote_violation', violation):
            if vote_form.is_valid():
                vote_form.save()
            else:
                print(252, vote_form.errors)
            return redirect(next)

        # report
        report_form = ReportViolationForm(
            request.POST, content=violation, user=user, prefix='report')
        if 'save_report' in request.POST.keys() and user.has_perm('users.can_report_violation', violation):
            if report_form.is_valid():
                report_form.save()
            else:
                print(253, report_form.errors)
            return redirect(next)

        # comment and override
        feedback_form = ResolveViolationForm(
            request.POST, violation=violation, user=user, prefix='feedback')
        if 'save_feedback' in request.POST.keys() and user.has_perm('users.can_comment_violation', violation):
            if feedback_form.is_valid():
                feedback_form.save()
            else:
                print(251, feedback_form.errors)
            return redirect(next)

        # theory_node
        if theory_node is not None:
            theorynode_form = TheoryForm(
                request.POST, instance=theory_node, user=user, prefix='theorynode')
            if 'save_theorynode' in request.POST.keys() and user.has_perm('theories.change_theorynode', theory_node):
                if theorynode_form.is_valid():
                    theory_node = theorynode_form.save()
                    theory_node.update_activity_logs(
                        user, verb=theorynode_form.get_verb())
                else:
                    print(250, theorynode_form.errors)
                return redirect(next)

    # GET request
    else:
        vote_form = VoteForm(
            instance=vote, violation=violation, user=user, prefix='vote')
        report_form = ReportViolationForm(
            content=violation, user=user, prefix='report')
        feedback_form = ResolveViolationForm(
            violation=violation, user=user, prefix='feedback')
        if theory_node is not None:
            theorynode_form = TheoryForm(
                instance=theory_node, user=user, prefix='theorynode')
        else:
            theorynode_form = None

    # Render
    context = {
        'violation':            violation,
        'related_violations':   related_violations,
        'user_violations':      user_violations,
        'feedback_form':        feedback_form,
        'report_form':          report_form,
        'vote_form':            vote_form,
        'theorynode_form':      theorynode_form,
        'revision_formset':     revision_formset,
        'parms':                parms,
        'prev':                 prev,
    }
    return render(
        request,
        'users/violation_resolve.html',
        context,
    )
