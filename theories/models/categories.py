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
import logging

from actstream.models import followers
from django.db import models
from django.db.models import Count
from django.template.defaultfilters import slugify
from django.urls import reverse

from core.utils import get_or_none, notify_if_unique, stream_if_unique
from theories.models.content import Content

# *******************************************************************************
# Defines
# *******************************************************************************
DEBUG = False
LOGGER = logging.getLogger('django')

# *******************************************************************************
# Models
# *******************************************************************************


class Category(models.Model):
    """A container for categories.

    A category is a collection of theories that tracks (through an activity stream) all changes
    to its theory set and any changes to its theories.

    Typical Usuage:
        * theory.categories.add(category)
        * theory.categories.remove(category)
        * category.get_all_theories()
        * category.update_activity_logs(user, verb, action_object)

    Model Attributes:
        slug (SlugField): The sluggified title (used for the url).
        title (CharField): The title of the category.

    Model Relations:
        objects (QuerySet:Category): The set of categories.
        theories (QuerySet:Content): The set of theories that belong to the category.
        target_actions (QuerySet:Actions): The category's activity stream, where the category
            was the target action.
        followers (QuerySet:Users): The set of user's following the category.
    """

    slug = models.SlugField()
    title = models.CharField(max_length=50)
    theories = models.ManyToManyField(Content, related_name='categories', blank=True)

    class Meta:
        """Where the model options are defined.

        Model metadata is “anything that’s not a field”, such as ordering options (ordering),
        database table name (db_table), or human-readable singular and plural names
        (verbose_name and verbose_name_plural). None are required, and adding class Meta to a
        model is completely optional.

        For more, see: https://docs.djangoproject.com/en/3.0/ref/models/options/
        """

        db_table = 'theories_category'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['title']

    def __str__(self):
        """Returns the category's title.

        Returns:
            str: The category's title (non-slugified).
        """
        return self.title

    def save(self, *args, **kwargs):
        """Save and automatically update the slug."""
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)
        return self

    @classmethod
    def get(cls, title, create=True):
        """Return the category model with the matching title

        Args:
            title (str): The title of the category (full or sluged).
            create (bool, optional): If true, and the category doesn't exist, then it is created.
                Defaults to False.

        Returns:
            Category: The category matching the title.
        """
        slug = slugify(title)
        category = get_or_none(cls.objects, slug=slug)
        if category is None and create:
            category = cls.objects.create(title=title, slug=slug)
        return category

    @classmethod
    def get_all(cls, exclude=None):
        """Get all categories not in exclude list.

        Args:
            exclude (list[str], optional): A list of category titles or slugs. Defaults to [].

        Returns:
            QuerySet: The set (QuerySet) of categories.
        """
        if exclude is not None:
            exclude_slugs = [slugify(x) for x in exclude]
            query_set = cls.objects.exclude(slug__in=exclude_slugs)
        else:
            query_set = cls.objects.all()
        return query_set.annotate(nTheories=Count('theories')).order_by('-nTheories')

    def get_absolute_url(self):
        """Return the url for viewing all theories within category.

        Returns:
            str: The url.
        """
        return reverse('theories:theories', kwargs={'category_slug': self.slug})

    def url(self):
        """Return the url for viewing all theories within category.

        Returns:
            str: The url.
        """
        return self.get_absolute_url()

    def activity_url(self):
        """Returns the action url for viewing the categories's activity feed.

        Returns:
            str: The url.
        """
        return reverse('theories:activity', kwargs={'category_slug': self.slug})

    def count(self):
        return self.theories.count()

    def get_theories(self):
        """Return all theories within category.

        Returns:
            list[Content]: The list of theories.
        """
        return self.theories.filter(content_type=Content.TYPE.THEORY)

    def update_activity_logs(self, user, verb, action_object=None):
        """Update the activity logs and notify the subscribers if the log is unique.

        Args:
            user (User): The user that conducted the action.
            verb (str): The verb describing the action.
            action_object (Content, optional): The object that the user modified.
                Defaults to None.
        """
        # Setup the log and update the activity log if unique.
        log = {'sender': user, 'verb': verb, 'action_object': action_object, 'target': self}
        if stream_if_unique(self.target_actions, log):
            # Notify each subscriber if the log is unique.
            for follower in followers(self):
                if follower != user:
                    log['recipient'] = follower
                    notify_if_unique(follower, log)
