r""" __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE.md file in the root directory of this source tree.
"""

import copy
import datetime
import enum
# *******************************************************************************
# Imports
# *******************************************************************************
import re

from actstream import action
from actstream.models import Action
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.http import urlencode
from model_utils import Choices as DjangoChoices
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
    """Get the current date and truncate the hours, min, seconds, ..."

    Returns:
        datetime: Today's date.
    """
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

    Raises:
        ValueError: If log is not a dict.
    """
    if not isinstance(log, dict):
        raise ValueError(f'log should be a dict, not {type(log)}.')
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

    Example: notify_if_unique(follower, log={'sender':self.user, "Bob farts", self.content})

    Args:
        follower (User): The user following the object.
        log (dict): A dict with the relevent log info ('sender', 'verb', 'action_object', 'target').
        update_unread (bool, optional): If enabled read messages are updated to unread.
            Defaults to True.
        accept_time (int, optional): The age in seconds that the log must be to be valid.
            Defaults to 21600.

    Returns:
        bool: True if the user has ben notified, false otherwise.

    Raises:
        ValueError: If log is not a dict.
    """
    if not isinstance(log, dict):
        raise ValueError(f'log should be a dict, not {type(log)}.')
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

    Raises:
        ValueError: If new_log is not a dict.
    """
    # Preconditions
    if not isinstance(new_log, dict):
        raise ValueError(f'new_log should be a dict, not {type(new_log)}.')

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
        for key, value in data.items():
            print("get_form_data:", key, value)

    # Return result
    return data


# *******************************************************************************
# Classes
# *******************************************************************************


class QuerySetDict():
    """A class for mimicking django's query sets.

    The dictionary keys can only integers or strings.

    Attributes:
        dict (dict): The container that stores the keys/objects for the query set.
        attrib_key (str): The
    """

    def __init__(self, attrib_key, queryset=None):
        """Initializer for QuerySetDict.

        Args:
            attrib_key (string): The attribute path for the lookup key. For example, suppose the
                objects being stored have an attribute content, which have a pk (primary key), then
                we would have attrib_key = 'content.pk'.
            queryset (QuerySet, optional): A django query set that is to be convert to QuerySetDict.
                Defaults to None.
        """
        self.dict = {}
        self.dict_iter = None
        self.attrib_key = attrib_key
        if queryset is not None:
            for x in queryset:
                self.dict[self.get_object_key(x)] = x

    def __str__(self):
        """Outputs a list of the stored items.

        Returns:
            str: The output.
        """
        return str(list(self))

    def __iter__(self):
        """Iterator initializer.

        Returns:
            QuerySetDict: A reference to self.
        """
        self.dict_iter = self.dict.values().__iter__()
        return self

    def __next__(self):
        """A getter for the next item in the dict.

        Returns:
            type(key): The key for the next dict item.
        """
        return self.dict_iter.__next__()

    def get_object_key(self, obj, attrib_key=None):
        """A getter for the object's primary key.

        Args:
            obj (Generic): The input object that contains attributes described by self.attrib_key
                or attrib_key.
            attrib_key (str or None): The attribute string that describes how to get the objects
                primary key.

        Returns:
            int or str: The object's primary key.

        Raises:
            ValueError: If key is not an int or a string.
        """
        key = obj
        if attrib_key is None:
            attrib_key = self.attrib_key
        for key_str in attrib_key.split('.'):
            key = getattr(key, key_str)
        if not isinstance(key, (int, str)):
            raise ValueError(f'key needs to be an int or a string, not {type(key)}.')
        return key

    def add(self, obj):
        """Adds the object to the dictionary.

        Args:
            obj (Generic): The object to add to the dictionary.
        """
        self.dict[self.get_object_key(obj)] = obj

    def get(self, *args, **kwargs):
        """A getter for retriving data from the dict.

        Args:
            *args, **kwargs (int,str,obj): A key or reference to the lookup object.

        Returns:
            Object: The stored object that matches the query or None if it doesn't exist.

        Raises:
            RuntimeError: If the number of arguements is anything other than 1.
            ValueError: If self.attrib_key is ill defined.
        """
        # Get key.
        if len(args) == 1:
            obj = args[0]
        elif len(kwargs) == 1:
            _key, obj = list(kwargs.items())[0]
        else:
            raise RuntimeError(
                'There has to be exactly one arguement.\n  args = {args}\n  kwargs = {kwargs}')
        if isinstance(obj, (int, str)):
            # Argument is a key.
            key = obj
        else:
            # Argument is a reference.
            if '.' in self.attrib_key:
                attrib_key = self.attrib_key[self.attrib_key.find('.') + 1:]
            else:
                raise ValueError(f'self.attrib_key ({self.attrib_key}) is malformed.')
            key = self.get_object_key(obj, attrib_key)
        # Get value.
        if key in self.dict.keys():
            return self.dict[key]
        return None

    def count(self):
        """A getter for the number of objects stored in the dict.

        Returns:
            int: The length of the dict.
        """
        return len(self.dict)

    def exclude(self, *args, **kwargs):
        """Not implemented yet.

        Returns:
            QuerySetDict: A reference to a QuerySetDict that does not contain the excluded objects.

        Raises:
            ValueError: If self.attrib_key is ill defined.
        """
        # Setup
        if '.' in self.attrib_key:
            attrib_key = self.attrib_key[self.attrib_key.find('.') + 1:]
        else:
            raise ValueError(f'self.attrib_key ({self.attrib_key}) is malformed.')
        # Get primary keys.
        keys = []
        for arg in args:
            if isinstance(arg, (int, str)):
                keys.append(arg)
            else:
                keys.append(self.get_object_key(arg, attrib_key))
        for _key_word, arg in kwargs.items():
            if isinstance(arg, (int, str)):
                keys.append(arg)
            else:
                keys.append(self.get_object_key(arg, attrib_key))
        # Create new QuerySetDict.
        new_query_set = copy.copy(self)
        new_query_set.dict = copy.copy(self.dict)
        for pk in keys:
            new_query_set.dict.pop(pk, None)
        # Done
        return new_query_set


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
            self.path = self.path.split(',')

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
        """Create a copy of the object.

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

    def get_object_key_value(self, key):
        """A getter for the key-value pair.

        Args:
            key (str): The key.

        Returns:
            str: The value.
        """
        value = self.params.get(key)
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        return value


class Choices(DjangoChoices):
    """An exention of model_utils.Choices

    The extension allows for set addition between two Choice objects (excludes duplicates).
    Additionally, there is one extra method to cleanly expose the database values (mainly used
    for queries such as status__in=CHOICES.get_values()).

    New attributes:
        unique (Bool): If true, the addition between two Choice objects will act as set addition
            with respect to _db_values.
    """
    unique = True

    def __init__(self, *choices, unique=True):
        super().__init__(*choices)
        self.unique = unique

    def __add__(self, other):
        triples = copy.deepcopy(self._triples)
        if isinstance(other, self.__class__):
            other_values = other._db_values
            other = other._triples
        else:
            other = list(other)
            other_values = set()
            for x in other:
                other_values.add(x[0])
        if self.unique:
            for i, triple in reversed(list(enumerate(triples))):
                if triple[0] in other_values:
                    del triples[i]
        return Choices(*(triples + other))

    def get_values(self):
        """A getter for the db values.

        Returns:
            [Generic]: A list of the db values.
        """
        return self._db_values
