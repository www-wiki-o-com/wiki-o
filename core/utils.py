"""      __      __    __                  __
        /  \    /  \__|  | _ __           /   \
        \   \/\/   /  |  |/ /  |  ______ |  |  |
         \        /|  |    <|  | /_____/ |  |  |
          \__/\__/ |__|__|__\__|          \___/

A web service for sharing opinions and avoiding arguments

@file       core/utils.py
@brief      A collection of utility methods/classes
@details
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# imports
# *******************************************************************************
import re
import enum

from actstream import action
from actstream.models import Action
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from notifications.signals import notify


# *******************************************************************************
# defines
# *******************************************************************************
DEBUG = False


class LogDiffResult(enum.Enum):
    """Enum for log_is_different return result."""
    MATCH = 1
    DIFFERENT = 2
    UPDATED = 3


# *******************************************************************************
# methods
# *******************************************************************************


def get_or_none(objects, **kwargs):
    """
    Queries a data model for a matching object.

    @example    get_or_none(theory.opinions, user=current_user)
    @param[in]  objects: A reference to the model's objects.
    @param[in]  kwars: A list of keyword aruments for the query.
    @return     the unique matching object, None otherwise
    """
    try:
        return objects.get(**kwargs)
    except ObjectDoesNotExist:
        return None


def get_first_or_none(objects, **kwargs):
    """
    Queries a data model for the first matching object.

    @example    get_or_none(TheoryNode.objects, created_by=current_user)
    @param[in]  objects: A reference to the model's objects.
    @param[in]  kwars: A list of keyword aruments for the query.
    @return     the first matching object, None otherwise
    """
    try:
        return objects.filter(**kwargs).first()
    except ObjectDoesNotExist:
        return None


def stream_if_unique(target_actions, log, accept_time=21600):
    """
    Checks if the input log(s) contents are different than the input parameters.

    @example    if log_is_different(log, self.user, "Bob creates a theory", self.theory): ...
    @param[in]  target_actions: The log to query
    @param[in]  log: A dict with the log info ('user', 'verb', 'action_object', 'target')
    @param[in]  update_unread: If read, update
    @param[in]  accept_time: The age in seconds that the log must be to be valid.
    @return     Enum result.
    """
    assert isinstance(log, dict)
    last_action = target_actions.first()
    result = log_is_different(last_action, log, accept_time=accept_time)
    if result == LogDiffResult.DIFFERENT:
        kwargs = log.copy()
        del kwargs['sender']
        action.send(log['sender'], **kwargs)
        return True
    return False


def notify_if_unique(follower, log, update_unread=True, accept_time=21600):
    """
    Checks if the input log(s) contents are different than the input parameters.

    @example    notify_if_unique(follower, log={self.user, "Bob farts", self.theory})
    @param[in]  log: The context for the new log.
                May contain the following keys:
                    actor: The user/object responsible for the action.
                    verb: The phrase that identifies the action.
                    action_object: The object linked to the action.
                    target: The object to which the action was performed.
    @param[in]  update_unread: If read, update
    @param[in]  accept_time: The age in seconds that the log must be to be valid.
    @return     Enum result.
    """
    assert isinstance(log, dict)
    last_notification = follower.notifications.first()
    result = log_is_different(last_notification, log, update_unread, accept_time)
    if result == LogDiffResult.DIFFERENT:
        notify.send(**log)
        return True
    return False


def log_is_different(old_log, new_log, update_unread=False, accept_time=21600):
    """
    Checks if the input log's contents are different than the input parameters.

    @example    log_is_different(old_log, new_log={'sender':self.user, 'verb':'Bob farts'})
    @param[in]  old_log: The old log to compare against
    @param[in]  new_log: The new log (a dict) user for comparision
                May contain the following keys:
                    sender: The user/object responsible for the action.
                    verb: The phrase that identifies the action.
                    action_object: The object linked to the action.
                    target: The object to which the action was performed.
    @param[in]  update_unread: If the old log has been read and the new log is different,
                change it to unread.
    @param[in]  accept_time: The age in seconds that the log must be to be valid.
    @return     Enum result.
    """
    # Preconditions
    assert isinstance(new_log, dict)

    # Test if log is different
    if old_log is None:
        return LogDiffResult.DIFFERENT
    if old_log.actor != new_log.get('sender'):
        return LogDiffResult.DIFFERENT
    if old_log.verb != new_log.get('verb'):
        return LogDiffResult.DIFFERENT
    if old_log.action_object != new_log.get('action_object'):
        return LogDiffResult.DIFFERENT
    if old_log.target != new_log.get('target'):
        return LogDiffResult.DIFFERENT

    # The log matches but it's too old
    elapsed_time = timezone.now() - old_log.timestamp
    if elapsed_time.total_seconds() >= accept_time:
        return LogDiffResult.DIFFERENT

    # The log matches but it's read, mark it back to unread
    if update_unread and isinstance(old_log, Action) and old_log.read():
        old_log.mark_as_unread()
        return LogDiffResult.UPDATED

    # The log matches
    return LogDiffResult.MATCH


def get_form_data(response, verbose_level=0):
    """
    A helper method for parsing form data from a post response.

    @param[in]  response: The post respose.
    @param[in]  verbose_level (optional, default 0): The verbose level used for debugging.
    """

    # Preconditions
    if response.context is None or not hasattr(response.context, 'keys'):
        return None

    # Setup
    data = {}
    for content_name in response.context.keys():
        # Parse a formsets
        if re.search(r'formset', content_name):
            formset = response.context[content_name]

            # Parse the formset managmenet data
            form = formset.management_form
            for field in form.fields.keys():
                data['%s-%s' % (form.prefix, field)] = form[field].value()

            # Parse each set of form data
            for form in formset.forms:
                for field in form.fields.keys():
                    if form[field].value() is None:
                        data['%s-%s' % (form.prefix, field)] = ''
                    else:
                        data['%s-%s' % (form.prefix, field)] = form[field].value()

        # Parse a single form
        elif re.search(r'form', content_name):
            form = response.context[content_name]
            if not isinstance(form, bool):
                for field in form.fields.keys():
                    if form.prefix is None:
                        data['%s' % (field)] = form[field].value()
                    else:
                        data['%s-%s' % (form.prefix, field)] = form[field].value()

    # Print debug info
    if verbose_level >= 10:
        for x in data:
            print("get_form_data:", x, data[x])

    # Return result
    return data
