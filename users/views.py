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
from actstream.models import following
from allauth.account.views import PasswordChangeView
from core.utils import Parameters, get_first_or_none, get_page_list
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.forms import modelformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import unquote
from notifications.models import Notification
from reversion.models import Version
from theories.forms import EvidenceForm, TheoryForm, TheoryRevisionForm
from theories.models.categories import Category
from theories.models.content import Content
from theories.models.opinions import Opinion

from users.forms import (ReportViolationForm, ResolveViolationForm,
                         SelectNotificationForm, SelectViolationForm, UserForm,
                         VoteForm)
from users.models import User, Violation, ViolationVote

# *******************************************************************************
# Defines
# *******************************************************************************
MAX_NUM_PAGES = 5
NUM_ITEMS_PER_PAGE = 25

# *******************************************************************************
# Methods
# *******************************************************************************

# *******************************************************************************
# Classes
# *******************************************************************************


class CustomPasswordChangeView(PasswordChangeView):
    success_url = '/accounts/profile/'


def public_profile_view(request, pk):
    """The public page for a user's profile.

    Args:
        request (HttpRequest): The HTTP request.
        pk (int): The user's primary key.

    Returns:
        HttpResponse: The HTTP response.
    """
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
    params = Parameters(request)
    prev_url = request.META.get('HTTP_REFERER', '/')

    # Render
    context = {
        'user': user,
        'current_user': current_user,
        'public_opinions': public_opinions,
        'private_opinions': private_opinions,
        'num_soft_strikes': user.count_strikes(recent=True, expired=False),
        'num_hard_strikes': user.count_strikes(recent=True, expired=False),
        'num_expired_strikes': user.count_strikes(recent=False, expired=True),
        'num_total_strikes': user.count_strikes(recent=True, expired=True),
        'prev_url': prev_url,
        'params': params,
    }
    return render(
        request,
        'users/user_detail.html',
        context,
    )


def private_profile_view(request):
    """The private page for a user's profile.

    Args:
        request (HttpRequest): The HTTP request.

    Returns:
        HttpResponse: The HTTP response.
    """
    # Redirect
    if not request.user.is_authenticated:
        return redirect('theories:index')

    # Setup
    user = request.user

    # Navigation
    prev_url = reverse('users:profile-detail', kwargs={'pk': user.id})
    next_url = reverse('users:profile-detail', kwargs={'pk': user.id})

    # Post request
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid() and form.has_changed():
            form.save()
            return redirect(next_url)

    # Get request
    else:
        form = UserForm(instance=user)

    # Render
    context = {
        'form': form,
        'prev_url': prev_url,
    }
    return render(
        request,
        'users/user_edit_form.html',
        context,
    )


@login_required
def notifications_view(request):
    """The notifications view for the user.

    Args:
        request (HttpRequest): The HTTP request.

    Returns:
        HttpResponse: The HTTP response.
    """
    # Setup
    user = request.user
    opinions = following(user, Opinion)
    theories = following(user, Content)
    categories = following(user, Category)
    notifications = user.notifications.all()
    user_violations = user.violations.all()
    NotificationFormset = modelformset_factory(Notification, form=SelectNotificationForm, extra=0)
    ViolationFormset = modelformset_factory(Violation, form=SelectViolationForm, extra=0)

    # Pagination01
    page01 = request.GET.get('page01')
    paginator01 = Paginator(notifications, NUM_ITEMS_PER_PAGE)
    notifications = paginator01.get_page(page01)
    notifications.page_list = get_page_list(paginator01.num_pages, page01, MAX_NUM_PAGES)
    # Pagination02
    page02 = request.GET.get('page02')
    paginator02 = Paginator(user_violations, NUM_ITEMS_PER_PAGE)
    user_violations = paginator02.get_page(page02)
    user_violations.page_list = get_page_list(paginator02.num_pages, page02, MAX_NUM_PAGES)

    # Navigation
    next_url = request.META.get('HTTP_REFERER', '/')

    # Post request
    if request.method == 'POST':
        action = request.POST.get('action')
        formset01 = NotificationFormset(request.POST,
                                        queryset=notifications.object_list,
                                        prefix='notifications')
        formset02 = ViolationFormset(request.POST,
                                     queryset=user_violations.object_list,
                                     prefix='feedback')
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
            return redirect(next_url)

    # Get request
    else:
        formset01 = NotificationFormset(queryset=notifications.object_list, prefix='notifications')
        formset02 = ViolationFormset(queryset=user_violations.object_list, prefix='feedback')

    # Render
    context = {
        'notifications': notifications,
        'user_violations': user_violations,
        'opinions': opinions,
        'theories': theories,
        'categories': categories,
        'formset01': formset01,
        'formset02': formset02,
    }
    return render(
        request,
        'users/user_notifications.html',
        context,
    )


def violation_index_view(request):
    """The page for viewing all violations.

    Args:
        request (HttpRequest): The HTTP request.

    Returns:
        HttpResponse: The HTTP response.
    """
    # Setup
    date = request.GET.get('date', None)
    violations = Violation.objects.all()

    # Violations
    if date is not None:
        date = unquote(date)
        violations = violations.filter(modified_date__gte=date)

    # Search
    search_term = request.GET.get('search', '')
    if len(search_term) > 0:
        violations = violations.filter(offender__username__icontains=search_term)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(violations, NUM_ITEMS_PER_PAGE)
    violations = paginator.get_page(page)
    violations.page_list = get_page_list(paginator.num_pages, page, MAX_NUM_PAGES)

    # Navigation
    params = Parameters(request)

    # Render
    context = {
        'violations': violations,
        'date_filter': date,
        'params': params,
    }
    return render(
        request,
        'users/violation_index.html',
        context,
    )


def violation_resolve_view(request, pk):
    """The public view for the violation.

    Args:
        request (HttpRequest): The HTTP request.
        pk (int): The primary key for the violation.

    Returns:
        HttpResponse: The HTTP response.
    """
    # Setup
    user = request.user
    violation = get_object_or_404(Violation, pk=pk)
    related_violations = violation.content.violations.exclude(pk=pk)
    user_violations = violation.offender.violations.exclude(pk=pk)
    vote = get_first_or_none(violation.votes.all(), user=user)
    if vote is None:
        vote = ViolationVote(violation=violation, user=user)

    # Content - content
    content_type = violation.content_type.model
    if content_type == 'content':
        content = violation.content
        revisions = content.get_revisions().filter(
            revision__date_created__date__lte=violation.pub_date)
        RevisionFormSet = modelformset_factory(Version, form=TheoryRevisionForm, extra=0)
        revision_formset = RevisionFormSet(queryset=revisions,
                                           form_kwargs={
                                               'user': user,
                                               'hide_delete': True
                                           })
    else:
        content = None
        revision_formset = []

    # Navigation
    params = Parameters(request)
    prev_url = reverse('users:violations') + params
    next_url = reverse('users:violation-resolve', kwargs={'pk': pk}) + params

    # Post request
    if request.method == 'POST':

        # Vote
        vote_form = VoteForm(request.POST,
                             instance=vote,
                             violation=violation,
                             user=user,
                             prefix='vote')
        if 'save_vote' in request.POST.keys() and \
                user.has_perm('users.can_vote_violation', violation):
            if vote_form.is_valid():
                vote_form.save()
            return redirect(next_url)

        # Report
        report_form = ReportViolationForm(request.POST,
                                          content=violation,
                                          user=user,
                                          prefix='report')
        if 'save_report' in request.POST.keys() and \
                user.has_perm('users.can_report_violation', violation):
            if report_form.is_valid():
                report_form.save()
            return redirect(next_url)

        # Comment and override
        feedback_form = ResolveViolationForm(request.POST,
                                             violation=violation,
                                             user=user,
                                             prefix='feedback')
        if 'save_feedback' in request.POST.keys() and \
                user.has_perm('users.can_comment_violation', violation):
            if feedback_form.is_valid():
                feedback_form.save()
            else:
                print(340, feedback_form.errors)
            return redirect(next_url)

        # Display the content in contention.
        if content is not None:
            if content.is_theory():
                content_form = TheoryForm(request.POST,
                                          instance=content,
                                          user=user,
                                          prefix='content')
                if 'save_content' in request.POST.keys() and \
                        user.has_perm('theories.change_content', content):
                    if content_form.is_valid():
                        content = content_form.save()
                        content.update_activity_logs(user, verb=content_form.get_verb())
                    return redirect(next_url)
            else:
                content_form = EvidenceForm(request.POST,
                                            instance=content,
                                            user=user,
                                            prefix='content')
                if 'save_content' in request.POST.keys() and \
                        user.has_perm('theories.change_content', content):
                    if content_form.is_valid():
                        content = content_form.save()
                        content.update_activity_logs(user, verb=content_form.get_verb())
                    return redirect(next_url)
        else:
            content_form = None

    # Get request
    else:
        vote_form = VoteForm(instance=vote, violation=violation, user=user, prefix='vote')
        report_form = ReportViolationForm(content=violation, user=user, prefix='report')
        feedback_form = ResolveViolationForm(violation=violation, user=user, prefix='feedback')
        if content is not None:
            content_form = TheoryForm(instance=content, user=user, prefix='content')
        else:
            content_form = None

    # Render
    context = {
        'violation': violation,
        'related_violations': related_violations,
        'user_violations': user_violations,
        'feedback_form': feedback_form,
        'report_form': report_form,
        'vote_form': vote_form,
        'content_form': content_form,
        'revision_formset': revision_formset,
        'params': params,
        'prev_url': prev_url,
    }
    return render(
        request,
        'users/violation_resolve.html',
        context,
    )
