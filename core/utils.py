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
# Imports
# *******************************************************************************
import re
import enum
import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.http import urlencode

from actstream import action
from actstream.models import Action
from notifications.signals import notify

# *******************************************************************************
# Defines
# *******************************************************************************
DEBUG = False


class LogDiffResult(enum.Enum):
    """Enum for log_is_different return result."""
    MATCH = 1
    DIFFERENT = 2
    UPDATED = 3


# *******************************************************************************
# General methods
# *******************************************************************************


def timezone_today():
    now = timezone.now()
    return datetime.date(now.year, now.month, now.day)


def string_to_list(input_string, braces='[]'):
    """Convert a string to a list.

    Args:
        input_string (str): The string to parse.
        braces (str): The set of braces to interpret.

    Returns:
        list: The list.
    """
    left_brace = braces[0]
    right_brace = braces[1]
    result = []
    for x in input_string.lstrip(left_brace).rstrip(right_brace).split(','):
        x = x.strip("'").strip()
        if len(x) > 0:
            if x[0] == left_brace and x[-1] == right_brace:
                x = string_to_list(x, braces)
            result.append(x)
    return result


def list_to_string(input_list):
    """Convert a list to a string.

    Args:
        input_list (list:obj): The input list.

    Returns:
        str: The string.
    """
    result = ''
    if len(input_list) > 0:
        for x in input_list:
            result += str(x) + ','
    result = result.strip(',')
    return result


# *******************************************************************************
# Model methods
# *******************************************************************************


def get_or_none(objects, **kwargs):
    """Queries a data model for a matching object.

    Example: get_or_none(theory.opinions, user=current_user)

    Args:
        objects (QuerySet): A reference to the model's objects.

    Returns:
        Object or None: The unique matching object, None otherwise.
    """
    try:
        return objects.get(**kwargs)
    except ObjectDoesNotExist:
        return None


def get_first_or_none(objects, **kwargs):
    """Queries a data model for the first matching object.

    Args:
        objects (QuerySet): A reference to the model's objects.

    Returns:
        Object or None: The unique matching object, None otherwise.
    """
    try:
        return objects.filter(**kwargs).first()
    except ObjectDoesNotExist:
        return None


def stream_if_unique(target_actions, log, accept_time=21600):
    """Checks if the input log(s) contents are different than the input parameters.

    Example: stream_if_unique(self.targets, log={'sender':self.user, 'verb':'Bob creates a theory'})

    Args:
        target_actions (Actions or Steam): The set of logs to compare against.
        log (dict): A dict with the relevent log info ('sender', 'verb', 'action_object', 'target').
        accept_time (int, optional): The age in seconds that the log must be to be valid.
            Defaults to 21600.

    Returns:
        bool: True if updated, false otherwise.
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
    """Checks if the input log(s) contents are different than the input parameters.

    Example: notify_if_unique(follower, log={'sender':self.user, "Bob farts", self.theory})

    Args:
        follower (User): The user following the object.
        log (dict): A dict with the relevent log info ('sender', 'verb', 'action_object', 'target').
        update_unread (bool, optional): If enabled read messages are updated to unread.
            Defaults to True.
        accept_time (int, optional): The age in seconds that the log must be to be valid.
            Defaults to 21600.

    Returns:
        bool: True if the user has ben notified, false otherwise.
    """
    assert isinstance(log, dict)
    last_notification = follower.notifications.first()
    result = log_is_different(last_notification, log, update_unread, accept_time)
    if result == LogDiffResult.DIFFERENT:
        notify.send(**log)
        return True
    return False


def log_is_different(old_log, new_log, update_unread=False, accept_time=21600):
    """Checks if the input log's contents are different than the input parameters.

    Example: log_is_different(old_log, new_log={'sender':self.user, 'verb':'Bob farts'})

    Args:
        old_log (Log): The exsiting log to compare against.
        new_log (dict): The new log.
        update_unread (bool, optional): If the old log has been read and the new log is different,
            change it to unread. Defaults to False. May contain the following keys:
                sender: The user/object responsible for the action.
                verb: The phrase that identifies the action.
                action_object: The object linked to the action.
                target: The object to which the action was performed.
        accept_time (int, optional): The age in seconds that the log must be to be valid.
            Defaults to 21600.

    Returns:
        LogDiffResult: May return DIFFERENT, MATCHED, or UPDATED.
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


# *******************************************************************************
# View methods
# *******************************************************************************


def get_page_list(num_pages, page, max_num_pages=5):
    """A helper method for constructing Paginator page links.

    Args:
        num_pages (int): [description]
        page (int): [description]
        max_num_pages (int, optional): [description]. Defaults to 5.

    Returns:
        list[int]: A list of page numbers to display.
    """
    if page is None:
        page = 1
    page = int(page)
    high_index = min(num_pages + 1, page + max_num_pages // 2 + 1)
    low_index = high_index - max_num_pages
    while low_index < 1:
        low_index += 1
        high_index += 1
    low_index = max(1, low_index)
    high_index = min(high_index, num_pages + 1)
    return range(low_index, high_index)


def get_form_data(response, verbose_level=0):
    """A helper method for parsing form data from a post response.

    Args:
        response (dict): The post respose.
        verbose_level (int, optional): The verbose level used for debugging. Defaults to 0.

    Returns:
        data: A more consise set of form data.
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


# *******************************************************************************
# Classes
# *******************************************************************************


class QuerySetDict():
    """A class for converting query sets into dicts.

    Attributes:
        dict (dict):
    """

    def __init__(self, attrib_key, queryset=None):
        """Todo

        Args:
            attrib_key ([type]): [description]
            queryset ([type], optional): [description]. Defaults to None.

        Returns:
            [type]: [description]
        """
        self.dict = {}
        self.dict_iter = None
        self.attrib_key = attrib_key
        if queryset is not None:
            for x in queryset:
                self.dict[self.get_key(x)] = x

    def __iter__(self):
        """Todo

        Returns:
            [type]: [description]
        """
        self.dict_iter = self.dict.values().__iter__()
        return self

    def __next__(self):
        """Todo

        Returns:
            [type]: [description]
        """
        return self.dict_iter.__next__()

    def __str__(self):
        """Todo

        Returns:
            [type]: [description]
        """
        return str(list(self))

    def get_key(self, obj):
        """Todo

        Args:
            obj ([type]): [description]

        Returns:
            [type]: [description]
        """
        key = obj
        for key_str in self.attrib_key.split('.'):
            key = getattr(key, key_str)
        return key

    def add(self, x):
        """Todo

        Args:
            x ([type]): [description]

        Returns:
            [type]: [description]
        """
        self.dict[self.get_key(x)] = x

    def get(self, key):
        """Todo

        Args:
            key ([type]): [description]

        Returns:
            [type]: [description]
        """
        if key in self.dict.keys():
            return self.dict[key]
        else:
            return None

    def count(self):
        """Todo

        Returns:
            [type]: [description]
        """
        return len(self.dict)


class Parameters():
    """A manager for url parameters.

    Use this class for managing url parameters (get and set).

    Attributes:
        pk (int): The primary key for the object being viewed.
        path (list:int): A history of primary keys that were visited before this object.
        flags (set:str): A set of flags.
        slug (str): The value of the slug.
        keys (set:str): A set of keys to be used for key-value pairs.
        params (): The set of parameters encoded in the url request.
        request (HttpRequest): The HTTP request.
    """

    def __init__(self, request, pk=None):
        """Constructor."""

        # Setup
        self.pk = pk
        self.path = []
        self.flags = []
        self.keys = set()
        self.request = request

        self.params = dict(request.GET)
        self.path = request.GET.get('path', '')
        self.flags = request.GET.get('flags', '')
        self.slug = request.GET.get('slug', '')

        # Path
        if self.path == '':
            self.path = []
        else:
            self.path = [int(x) for x in re.findall(r'\d+', self.path)]

        # Flags
        self.flags = string_to_list(self.flags)

    def __str__(self):
        """Output the url parameter string.

        Returns:
            str: The parameter string (including the "?").
        """
        params = {}
        if len(self.path) > 0:
            params['path'] = list_to_string(self.path)
        if len(self.flags) > 0:
            params['flags'] = list_to_string(self.flags)
        if self.slug != '':
            params['slug'] = self.slug
        for key in self.keys:
            params[key] = self.params[key]
        s = '?%s' % urlencode(params)
        s = s.rstrip('?')
        return s

    def __add__(self, right_object):
        """Addition operator (from the right).
        Args:
            right_object (obj): The other object for addition, will be treated as a string.

        Returns:
            str: The resultant expression of str(left) + str(self)
        """
        return str(self) + str(right_object)

    def __radd__(self, left_object):
        """Addition operator (from the left).

        Args:
            left_object (obj): The other object for addition, will be treated as a string.

        Returns:
            str: The resultant expression of str(left) + str(self)
        """
        return str(left_object) + str(self)

    def get_path(self):
        """A getter for the path.

        Returns:
            list:int: The path of object primary keys.
        """
        return self.path

    def get_new(self):
        """"Create a copy of the object.

        Returns:
            Parameters: A copy of the object.
        """
        cls = self.__class__
        x = cls(self.request, self.pk)
        return x

    def get_prev(self):
        """Generate a new object for going back to the previous object.

        Returns:
            Parameters: The new object.
        """
        cls = self.__class__
        x = cls(self.request)
        if len(x.path) > 0:
            x.path.pop()
        return x

    def get_next(self):
        """Generate a new object for going to the next object.

        Returns:
            Parameters: The new object.
        """
        cls = self.__class__
        x = cls(self.request)
        if self.pk is not None:
            x.path.append(self.pk)
        return x

    def get_slug(self):
        """A getter for the slug value.

        Returns:
            str: The value of the slug.
        """
        return self.slug

    def set_slug(self, value):
        """A setter for the value value.

        Args:
            value (str): The value.

        Returns:
            Parameters: A reference to this object.
        """
        self.slug = value
        return self

    def add_key_value(self, key, value):
        """Add a key-value pair to the parameter list.

        Args:
            key (str): The key.
            value (str): The value.

        Returns:
            Parameters: A reference to this object.
        """
        self.params[key] = value
        self.keys.add(key)
        return self

    def get_key_value(self, key):
        """A getter for the key-value pair.

        Args:
            key (str): The key.

        Returns:
            str: The value.
        """
        value = self.params.get(key, None)
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        return value
