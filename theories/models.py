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
import re
import copy
import rules
import numpy
import random
import inspect
import logging
import datetime
import reversion

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Sum, F, Q
from django.template.defaultfilters import slugify
from django.contrib.contenttypes.fields import GenericRelation
from model_utils import Choices
from actstream import action
from actstream.models import followers
from actstream.actions import is_following
from notifications.signals import notify
from reversion.models import Version
from hitcount.models import HitCount
from hitcount.views import HitCountMixin

from users.models import User, Violation
from core.utils import QuerySetDict
from core.utils import get_or_none, get_first_or_none
from core.utils import stream_if_unique, notify_if_unique
from theories.abstract_models import TheoryPointerBase, DependencyPointerBase

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


@reversion.register(fields=['content_type', 'title00', 'title01', 'details'])
class Content(models.Model):
    """A container for theory, evidence, and sub-theory data.

    Attributes:
        title00 (str):
        title01 (str):
        details (str):
        content_type (TYPE):
        categories (QuerySet:Category):
        pub_date (DateField):
        created_by (User):
        modified_by (User):
        modified_date (DateField):
        utilization (int):
        rank (int):
        dependencies (QuerySet:Content):
        flat_dependencies (QuerySet:Content):
        violations (Violation):

    Related model attributes:
        users (QuerySet:User): The set of user's that formed an opinion on this theory.
    """

    TYPE = Choices(
        (10, 'THEORY', ('Theory')),
        (20, 'EVIDENCE', ('Evidence (other)')),
        (21, 'FACT', ('Evidence (fact)')),
        (-10, 'DELETED_THEORY', ('Deleted Theory')),
        (-20, 'DELETED_EVIDENCE', ('Deleted Evidence (other)')),
        (-21, 'DELETED_FACT', ('Deleted Evidence (fact)')),
    )

    # Variables
    INTUITION_PK = -1
    content_type = models.SmallIntegerField(choices=TYPE)
    title00 = models.CharField(max_length=255, blank=True, null=True)
    title01 = models.CharField(max_length=255, unique=True)
    details = models.TextField(max_length=10000, blank=True)
    categories = models.ManyToManyField(Category, related_name='theories', blank=True)

    pub_date = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(User,
                                   models.SET_NULL,
                                   related_name='created_dependencies',
                                   blank=True,
                                   null=True)
    modified_by = models.ForeignKey(User,
                                    models.SET_NULL,
                                    related_name='edited_dependencies',
                                    blank=True,
                                    null=True)
    modified_date = models.DateTimeField(models.SET_NULL, blank=True, null=True)

    utilization = models.IntegerField(default=0)
    rank = models.SmallIntegerField(default=0)
    dependencies = models.ManyToManyField('self',
                                          related_name='parents',
                                          symmetrical=False,
                                          blank=True)
    flat_dependencies = models.ManyToManyField('self',
                                               related_name='parent_flat_theories',
                                               symmetrical=False,
                                               blank=True)

    violations = GenericRelation(Violation)

    # Cache attributes
    saved_stats = None
    saved_dependencies = None
    saved_flat_dependencies = None
    saved_parents = None
    saved_opinions = None

    class Meta:
        """Where the model options are defined.

        Model metadata is “anything that’s not a field”, such as ordering options (ordering),
        database table name (db_table), or human-readable singular and plural names
        (verbose_name and verbose_name_plural). None are required, and adding class Meta to a
        model is completely optional.

        For more, see: https://docs.djangoproject.com/en/3.0/ref/models/options/
        """
        ordering = ['-rank']
        db_table = 'theories_content'
        verbose_name = 'Content'
        verbose_name_plural = 'Content'
        permissions = (
            ('swap_title', 'Can swap true/false title.'),
            ('change_title', 'Can change title.'),
            ('change_details', 'Can change details.'),
            ('delete_reversion', 'Can delete revision.'),
            ('merge_content', 'Can merge dependencies.'),
            ('backup_content', 'Can create backup.'),
            ('remove_content', 'Can remove content.'),
            ('restore_content', 'Can restore/revert from revision.'),
            ('convert_content', 'Can convert theory <=> evidence.'),
        )

    def __str__(self, true_points=1, false_points=0):
        """Returns title01 for evidence and true theories, otherwise title00, which represents the false title."""
        s = ''
        if self.is_evidence():
            s = self.title01
        elif true_points >= false_points:
            s = self.get_true_statement()
        else:
            s = self.get_false_statement()
        if self.is_deleted():
            s += ' (deleted)'
        return s

    def get_categories(self):
        return self.categories.all()

    def get_title(self):
        self.assert_evidence()
        return self.title01

    def get_true_statement(self):
        self.assert_theory()
        return self.title01

    def get_false_statement(self):
        self.assert_theory()
        if self.title00 is None or self.title00 == '':
            return '%s, is false.' % self.title01.strip('.')
        else:
            return self.title00

    def about(self):
        """Returns a string with a title and details."""
        return '%s\n\n%s' % (self.title01, self.details)

    def get_absolute_url(self):
        """Returns the url for viewing the object's details."""
        if self.is_theory():
            return reverse('theories:theory-detail', kwargs={'content_pk': self.pk})
        return reverse('theories:evidence-detail', kwargs={'content_pk': self.pk})

    def url(self):
        """Returns the url for viewing the object's details."""
        return self.get_absolute_url()

    def activity_url(self):
        """Returns the action url for viewing the object's activity feed."""
        if self.is_theory():
            return reverse('theories:theory-activity', kwargs={'content_pk': self.pk})
        else:
            return reverse('theories:evidence-activity', kwargs={'content_pk': self.pk})

    def restore_url(self):
        """Returns the url for viewing the object's revisions."""
        if self.is_theory():
            return reverse('theories:theory-restore', kwargs={'content_pk': self.pk})
        else:
            return reverse('theories:evidence-restore', kwargs={'content_pk': self.pk})

    def tag_id(self):
        """Returns a unique id string used for html visibility tags."""
        return 'TN%03d' % self.pk

    def is_deleted(self):
        """Returns true if dependency is a theory."""
        return self.content_type < 0

    def is_root(self):
        """Returns true if dependency is a theory and in a category."""
        self.assert_theory()
        return self.categories.count() > 0

    def is_theory(self):
        """Returns true if dependency is a theory."""
        return abs(self.content_type) == self.TYPE.THEORY

    def is_subtheory(self):
        """Returns true if dependency is a theory."""
        return self.is_theory()

    def is_evidence(self):
        """Returns true if dependency is evidence."""
        return abs(self.content_type) == self.TYPE.FACT or abs(
            self.content_type) == self.TYPE.EVIDENCE

    def is_fact(self):
        """Returns true if dependency is factual evidence (verifiable)."""
        self.assert_evidence()
        return self.is_verifiable()

    def is_verifiable(self):
        """Returns true if dependency is factual evidence (verifiable)."""
        self.assert_evidence()
        return abs(self.content_type) == self.TYPE.FACT

    def assert_theory(self, check_dependencies=False):
        if self.is_evidence():
            stack01 = inspect.stack()[1]
            stack02 = inspect.stack()[2]
            error = 'Error (%s): This dependency should not be evidence (pk=%d).\n' % (
                timezone.now().strftime("%Y-%m-%d %X"), self.pk)
            error += '  Traceback[1]: %s, %d, %s, %s \n' % (
                stack01[1].split('code')[-1], stack01[2], stack01[3], stack01[4][0].strip())
            error += '  Traceback[2]: %s, %d, %s, %s \n' % (
                stack02[1].split('code')[-1], stack02[2], stack02[3], stack02[4][0].strip())
            LOGGER.error(error)
            if self.dependencies.count() > 0:
                LOGGER.error(
                    'Content.assert_theory: This dependency should not have dependencies (pk=%d).',
                    self.pk)
            if self.flat_dependencies.count() > 0:
                LOGGER.error(
                    'Content.assert_theory: This dependency should not have flat dependencies (pk=%d).',
                    self.pk)
            return False
        elif check_dependencies:
            if self.flat_dependencies.filter(content_type__lt=0).exists():
                LOGGER.error(
                    'Content.assert_theory: There should not be any flat deleted dependencies (pk=%d).',
                    self.pk)
                return False
        return True

    def assert_evidence(self, check_dependencies=False):
        if self.is_theory():
            stack01 = inspect.stack()[1]
            stack02 = inspect.stack()[2]
            error = 'Error: This dependency should not be a theory (pk=%d).\n' % self.pk
            error += '  Traceback[1]: %s, %d, %s, %s \n' % (
                stack01[1].split('code')[-1], stack01[2], stack01[3], stack01[4][0].strip())
            error += '  Traceback[2]: %s, %d, %s, %s \n' % (
                stack02[1].split('code')[-1], stack02[2], stack02[3], stack02[4][0].strip())
            LOGGER.error(error)
            return False
        elif check_dependencies:
            if self.dependencies.count() > 0:
                LOGGER.error('592: This dependency should not have dependencies (pk=%d).' % self.pk)
                return False
            if self.flat_dependencies.count() > 0:
                LOGGER.error('593: This dependency should not have flat dependencies (pk=%d).' %
                             self.pk)
                return False
        return True

    def save(self, user=None, *args, **kwargs):
        """Automatically adds stats and intuition dependencies."""
        if user is not None:
            self.modified_by = user
            self.modified_date = timezone.now()
            if self.pk is None:
                self.created_by = user
        super().save(*args, **kwargs)
        if self.is_theory():
            Stats.initialize(self)
            self.flat_dependencies.add(self.get_intuition())
        return self

    def autosave(self, user, force=False, *args, **kwargs):
        """Todo

        Args:
            user ([type]): [description]
            force (bool, optional): [description]. Defaults to False.

        Returns:
            [type]: [description]

        Todo:
            * Do not save if datetime matches.
        """
        rev_user = None
        save_rev = False
        if self.modified_by is not None and self.modified_by != user:
            save_rev = True
            rev_user = self.modified_by
        elif force:
            save_rev = True
            rev_user = user
        if save_rev:
            with reversion.create_revision():
                self.save()
                reversion.set_user(rev_user)
                reversion.set_comment('Autosave')

    def save_snapshot(self, user, *args, **kwargs):
        """Create a snapshot of the title(s) and details."""
        # get and delete user's previous snapshots
        for revision in self.get_revisions().filter(revision__user=user,
                                                    revision__comment='Snapshot'):
            revision.delete()
        # create new snapshot
        with reversion.create_revision():
            super().save(*args, **kwargs)
            reversion.set_user(user)
            reversion.set_comment('Snapshot')

    def swap_titles(self, user=None):
        """Swap true false titles of theory and permeate the changes to opinions and stats.

        Args:
            user ([type], optional): [description]. Defaults to None.

        Returns:
            [type]: [description]

        Todo:
            * Improve stats calculation.
            * Add assert.
        """
        # error checking
        if not self.assert_theory():
            return False
        # setup
        if user is None:
            user = User.get_system_user()
        # theory dependency
        self.title00, self.title01 = self.title01, self.title00
        self.save()
        # opinions
        for opinion in self.get_opinions():
            opinion.swap_true_false()
            notify.send(
                sender=user,
                recipient=opinion.user,
                verb=
                """<# object.url The theory, "{{ object }}" has had its true and false titles swapped. #>""",
                description='This should not effect your <# target.url opinion #> in anyway.',
                action_object=self,
                target=opinion,
                level='warning',
            )
        # stats
        for stats in self.get_all_stats():
            stats.swap_true_false()
        return True

    def convert(self, user=None, verifiable=False):
        """Todo

        Args:
            user ([type], optional): [description]. Defaults to None.
            verifiable (bool, optional): [description]. Defaults to False.

        Returns:
            [type]: [description]

        Todo:
            * Allow evidence to have user opinions but not editable ones.
            * Go over notification logic.
        """
        # setup
        if user is None:
            user = User.get_system_user()
        if self.is_theory():
            # error checking
            if self.parents.count() == 0 or self.is_root():
                LOGGER.error('461: Cannot convert a root theory to evidence (pk=%d).' % self.pk)
                return False
            # inherit dependencies
            for parent_theory in self.get_parent_theories():
                for theory_dependency in self.get_dependencies():
                    parent_theory.add_dependency(theory_dependency)
            # clear stats
            for stats in self.get_all_stats():
                stats.delete()
            # convert theory dependency
            if verifiable:
                self.content_type = self.TYPE.FACT
            else:
                self.content_type = self.TYPE.EVIDENCE
            self.dependencies.clear()
            self.flat_dependencies.clear()
        else:
            self.content_type = self.TYPE.THEORY
        self.save(user)
        # notifications (opinions)
        if self.is_theory():
            for opinion in self.get_opinions():
                notify.send(
                    sender=user,
                    recipient=opinion.user,
                    verb=
                    '<# object.url The theory, "{{ object }}" has been converted to evidence. #>',
                    description=
                    'This change has rendered your <# target.url opinion #> unnecessary.',
                    action_object=self,
                    target=opinion,
                    level='warning',
                )
        # notifications (opinion_dependencies)
        for opinion in Opinion.objects.filter(dependencies__content__pk=self.pk):
            if self.is_evidence():
                verb = '<# object.url The theory, "{{ object }}" has been converted to evidence. #>'
            else:
                verb = '<# object.url The evidence, "{{ object }}" has been converted to a sub-theory. #>'
            notify.send(
                sender=user,
                recipient=opinion.user,
                verb=verb,
                description='This change affects your <# target.url opinion #> of {{ target }}.',
                action_object=self,
                target=opinion,
                level='warning',
            )
        return True

    def merge(self, content, user=None):
        """Merge this theory dependency with another, by absorbing the other dependency.

        Args:
            content ([type]): [description]
            user ([type], optional): [description]. Defaults to None.

        Returns:
            [type]: [description]

        Todo:
            * Delete stats.
        """
        # error checking
        if self.content_type != content.content_type:
            LOGGER.error(
                '496: Cannot merge theory dependencies of different type (pk01=%d, pk02=%d).' %
                (self.pk, content.pk))
            return False
        # setup
        if user is None:
            user = User.get_system_user()
        # theories
        if self.is_theory():
            # dependencies
            dependencies = content.get_dependencies().exclude(pk=self.pk)
            flat_dependencies = content.get_flat_dependencies().exclude(pk=self.pk)
            self.dependencies.add(*dependencies)
            self.flat_dependencies.add(*flat_dependencies)
            # opinions
            for opinion02 in content.get_opinions():
                opinion01 = get_or_none(self.get_opinions(), user=opinion02.user)
                if opinion01 is None:
                    theory = opinion02.content
                    theory.remove_from_stats(opinion02, cache=True, save=False)
                    opinion02.content = self
                    opinion02.save()
                    self.add_to_stats(opinion02, cache=True, save=False)
                else:
                    # notifications
                    log = {}
                    log['sender'] = user
                    log['recipient'] = opinion01.user  # TODO: might be a bug, should it be opinion02.user?
                    log['verb'] = '<# target.url "{{ target }}" has merged with "{{ object }}" and is now deleted. #>'
                    log['description'] = 'Please adjust your <# object.url opinion #> to reflect this change.'
                    log['action_object'] = opinion01
                    log['target'] = opinion02
                    log['level'] = 'warning'
                    notify_if_unique(opinion02.user,
                                     log)  # TODO: might be a bug, should it be opinion01.user?
            # stats
            content.save_stats()
            self.save_stats()
        # parents
        for parent in content.parents.filter(~Q(pk=self.pk)):
            parent.add_dependency(self)
        # opinion dependencies
        changed_theories = []
        for opinion_dependency02 in content.opinion_dependencies.all():
            opinion = opinion_dependency02.parent
            opinion_dependency01 = get_or_none(opinion.get_dependencies(), content=self)
            if opinion_dependency01 is None:
                theory = opinion.content
                theory.remove_from_stats(opinion, cache=True, save=False)
                opinion_dependency02.content = self
                opinion_dependency02.save()
                theory.add_to_stats(opinion, cache=True, save=False)
                changed_theories.append(theory)
            else:
                # notifications
                log = {}
                log['sender'] = user
                log['recipient'] = opinion.user
                log['verb'] = '<# object.url "{{ object }}" has gone through a merge that affects your opinion. #>'
                log['description'] = 'We apologize for the inconvenience. Please review your <# target.url opinion #> and adjust as necessary.'
                log['action_object'] = self
                log['target'] = opinion
                log['level'] = 'warning'
                notify_if_unique(opinion.user, log)
        # save changes
        for theory in changed_theories:
            theory.save_stats()
        # delete
        content.delete(user)
        return True

    def delete(self, user=None, soft=True):
        """Recursively deletes abandoned dependencies.

        Args:
            user ([type], optional): [description]. Defaults to None.
            soft (bool, optional): [description]. Defaults to True.

        Returns:
            [type]: [description]

        Todo:
            * Reset cache.
        """
        # error checking
        if self.pk == self.INTUITION_PK:
            LOGGER.error('720: Intuition dependency should not be deleted (pk=%d).' % self.pk)
            return False
        if self.is_deleted():
            LOGGER.error('721: Theory dependency is already deleted (pk=%d).' % self.pk)
            return False
        # setup
        if user is None:
            user = User.get_system_user()
        # delete
        self.content_type = -abs(self.content_type)
        # save
        if soft:
            self.save(user)
        else:
            super().delete()
        # recursive delete
        if self.is_theory():
            # cleanup evidence
            for evidence in self.get_theory_evidence():
                if evidence.get_parent_theories().count() == 0:
                    evidence.delete(user, soft)
            # cleanup sub-theories
            for subtheory in self.get_theory_subtheories():
                if not subtheory.is_root() and subtheory.get_parent_theories().count() == 0:
                    subtheory.delete(user, soft)
        # remove flat dependencies
        if soft:
            self.parent_flat_theories.clear()
            for parent in self.get_parent_theories():
                if self.is_theory():
                    exclude_list = list(parent.get_dependencies().values_list(
                        'pk', flat=True)) + [self.INTUITION_PK]
                    nested_dependencies = self.get_nested_dependencies().exclude(
                        pk__in=exclude_list)
                    for theory_dependency in nested_dependencies:
                        parent.remove_flat_dependency(theory_dependency)
            # notifications (opinion)
            if self.is_theory():
                for opinion in self.get_opinions():
                    notify.send(
                        sender=user,
                        recipient=opinion.user,
                        verb='<# object.url {{ object }} has been deleted. #>',
                        description=
                        'This change means that your <# target.url opinion #> of {{ target }} is no longer valid.',
                        action_object=self,
                        target=opinion,
                        level='warning',
                    )
            # notifications (opinion_dependency)
            for opinion in Opinion.objects.filter(dependencies__content__pk=self.pk):
                notify.send(
                    sender=user,
                    recipient=opinion.user,
                    verb='<# object.url {{ object }} has been deleted. #>',
                    description='Please update your <# target opinion #> to reflect the change.',
                    action_object=self,
                    target=opinion,
                    level='warning',
                )
        return True

    def cache(self, dependencies=True, flat_dependencies=True, stats=False):
        """Cache sub-theory and evidence dependencies to save on db calls."""
        # error checking
        if not self.assert_theory():
            return False
        if dependencies:
            self.get_dependencies(cache=True)
        if flat_dependencies:
            self.get_flat_dependencies(cache=True)
        if stats:
            self.get_all_stats(cache=True)
        return True

    def add_dependency(self, theory_dependency):
        """Add evidence or a sub-theory to this theory and update the flat dependencies."""
        if not self.assert_theory():
            return False
        self.add_dependencies([theory_dependency])
        return True

    def add_dependencies(self, theory_dependencies):
        """Add evidence or a sub-theory to this theory and update the flat dependencies."""
        # error checking
        if not self.assert_theory():
            return False
        # nested dependencies
        nested_flat_dependencies = []
        for theory_dependency in theory_dependencies:
            if theory_dependency.is_subtheory():
                nested_flat_dependencies += list(theory_dependency.get_nested_dependencies())
        # self
        self.dependencies.add(*theory_dependencies)
        self.flat_dependencies.add(*theory_dependencies, *nested_flat_dependencies)
        # parent dependencies
        for parent in self.climb_theory_dependencies():
            parent.flat_dependencies.add(*theory_dependencies, *nested_flat_dependencies)
        return True

    def remove_dependency(self, theory_dependency, user=None):
        # error checking
        if not self.assert_theory(check_dependencies=True):
            return False
        # setup
        if user is None:
            user = User.get_system_user()
        # remove from self.dependencies
        if theory_dependency in self.get_dependencies():
            self.dependencies.remove(theory_dependency)
            for opinion in self.get_opinions().filter(
                    dependencies__content__pk=theory_dependency.pk):
                notify.send(
                    sender=user,
                    recipient=opinion.user,
                    verb='<# object.url {{ object }} has been removed from {{ target }}. #>',
                    description='Please update your <# target.url opinion #> to reflect the change.',
                    action_object=theory_dependency,
                    target=opinion,
                    level='warning',
                )
        # remove from self.flat_dependencies
        self.remove_flat_dependency(theory_dependency, user=user)
        return True

    def remove_flat_dependency(self, theory_dependency, user=None):
        # error checking
        if not self.assert_theory(
                check_dependencies=True) or theory_dependency == self.get_intuition():
            return False
        if theory_dependency not in self.get_dependencies():
            nested = False
            for subtheory in self.get_theory_subtheories():
                if subtheory.get_dependencies().filter(id=theory_dependency.pk).exists():
                    nested = True
                    break
            if not nested:
                self.flat_dependencies.remove(theory_dependency)
                for parent in self.get_parent_theories():
                    if theory_dependency not in parent.get_dependencies():
                        parent.remove_flat_dependency(theory_dependency, user=user)
                return True
        return False

    @classmethod
    def update_intuition(cls, create=True):
        if cls.INTUITION_PK < 0:
            cls.get_intuition(create=True)

    @classmethod
    def get_intuition(cls, create=True):
        """Creates and returns an intuition dependency."""
        # assume intuition_pk is known
        try:
            intuition = cls.objects.get(pk=cls.INTUITION_PK)
            if intuition.title01 != 'Intuition':
                intuition = None
        except:
            intuition = None
        # get or create
        if create and intuition is None:
            intuition, created = cls.objects.get_or_create(content_type=cls.TYPE.EVIDENCE,
                                                           title01='Intuition')
            cls.INTUITION_PK = intuition.pk
        # blah
        return intuition

    def get_dependencies(self, deleted=False, cache=False):
        """Returns a query set of the theory's dependencies (use cache if available)."""
        # error checking
        if not self.assert_theory():
            return None
        # get non-deleted dependencies
        if self.saved_dependencies is not None:
            dependencies = self.saved_dependencies
        elif cache:
            self.saved_dependencies = self.dependencies.filter(content_type__gt=0)
            list(self.saved_dependencies)
            dependencies = self.saved_dependencies
        else:
            dependencies = self.dependencies.filter(content_type__gt=0)
        # get deleted dependencies
        if deleted:
            dependencies |= self.dependencies.filter(content_type__lt=0)
        return dependencies

    def get_flat_dependencies(self, deleted=False, cache=False, distinct=True):
        """Returns a query set of the theory's flat dependencies/nested evidence (use cache if available)."""
        # error checking
        if not self.assert_theory():
            return None
        # non-deleted dependencies
        if self.saved_flat_dependencies is not None:
            flat_dependencies = self.saved_flat_dependencies
        elif cache:
            self.saved_flat_dependencies = self.flat_dependencies.filter(
                Q(content_type=self.TYPE.FACT) | Q(content_type=self.TYPE.EVIDENCE))
            list(self.saved_flat_dependencies)
            flat_dependencies = self.saved_flat_dependencies
        else:
            flat_dependencies = self.flat_dependencies.filter(
                Q(content_type=self.TYPE.FACT) | Q(content_type=self.TYPE.EVIDENCE))
        # get deleted dependencies
        if deleted:
            # recursively build up dependencies
            flat_dependencies |= self.dependencies.filter(
                Q(content_type=-self.TYPE.FACT) | Q(content_type=-self.TYPE.EVIDENCE))
            for theory_dependency in self.dependencies.filter(content_type=-self.TYPE.THEORY):
                flat_dependencies |= theory_dependency.get_flat_dependencies(deleted=True,
                                                                             distinct=False)
            if distinct:
                flat_dependencies = flat_dependencies.distinct()
        return flat_dependencies

    def get_nested_dependencies(self, deleted=False, distinct=True):
        """Returns a query set of the theory's flat dependencies/nested evidence (use cache if available)."""
        # error checking
        if not self.assert_theory():
            return None
        # blah
        dependencies = self.flat_dependencies.filter(content_type__gt=0)
        if deleted:
            dependencies |= self.dependencies.filter(content_type__lt=0)
            for theory_dependency in self.dependencies.filter(content_type=-self.TYPE.THEORY):
                dependencies |= theory_dependency.get_nested_dependencies(deleted=True,
                                                                          distinct=False)
            if distinct:
                dependencies = dependencies.distinct()
        return dependencies

    def get_nested_subtheory_dependencies(self, deleted=False, distinct=True):
        """Returns a query set of the theory's flat dependencies/nested evidence (use cache if available)."""
        # error checking
        if not self.assert_theory():
            return None
        # blah
        dependencies = self.flat_dependencies.filter(content_type=self.TYPE.THEORY)
        if deleted:
            dependencies |= self.dependencies.filter(content_type=-self.TYPE.THEORY)
            for theory_dependency in self.dependencies.filter(content_type=-self.TYPE.THEORY):
                dependencies |= theory_dependency.get_nested_subtheory_dependencies(deleted=True,
                                                                                    distinct=False)
            if distinct:
                dependencies = dependencies.distinct()
        return dependencies

    def get_theory_evidence(self, deleted=False, cache=False):
        """Returns a query set of the theory's evidence."""
        # error checking
        if not self.assert_theory():
            return None
        # blah
        dependencies = self.get_dependencies().filter(
            Q(content_type=self.TYPE.FACT) | Q(content_type=self.TYPE.EVIDENCE))
        if deleted:
            dependencies |= self.dependencies.filter(
                Q(content_type=-self.TYPE.FACT) | Q(content_type=-self.TYPE.EVIDENCE))
        return dependencies

    def get_theory_subtheories(self, deleted=False, cache=False):
        """Returns a query set of the theory's sub-theories."""
        # error checking
        if not self.assert_theory():
            return None
        # blah
        dependencies = self.get_dependencies().filter(content_type=self.TYPE.THEORY)
        if deleted:
            dependencies |= self.dependencies.filter(content_type=-self.TYPE.THEORY)
        return dependencies

    def get_parent_theories(self, deleted=False, cache=False):
        """Returns a list of theories that are parents to this dependency (does not use cache)."""
        # get non-deleted dependencies
        if self.saved_parents is not None:
            parents = self.saved_parents
        elif cache:
            self.saved_parents = self.parents.filter(content_type__gt=0)
            list(self.saved_parents)
            parents = self.saved_parents
        else:
            parents = self.parents.filter(content_type__gt=0)
        # get deleted dependencies
        if deleted:
            parents |= self.parents.filter(content_type__lt=0)
        return parents

    def climb_theory_dependencies(self, qs=None):
        """Returns a query set of all ancestors of this theory."""
        cls = self.__class__
        if qs is None:
            qs = cls.objects.none()
        for parent in self.get_parent_theories():
            if parent not in qs:
                qs |= cls.objects.filter(pk=parent.pk)
                qs = qs | parent.climb_theory_dependencies(qs)
        return qs

    def get_opinions(self, cache=False, exclude=None):
        """Return a list opinions pertaining to theory."""
        # error checking
        self.assert_theory()
        # queryset
        opinions = self.opinions.filter(deleted=False)
        if self.saved_opinions is not None:
            opinions = self.saved_opinions
        elif cache:
            self.saved_opinions = opinions
            list(opinions)
        if exclude is not None:
            opinions = opinions.exclude(user=exclude)
        return opinions

    def get_opinion_dependencies(self, cache=False, exclude=None):
        """Return a list opinions pertaining to theory."""
        opinion_dependencies = self.opinion_dependencies.filter(parent__deleted=False)
        if self.saved_opinion_dependencies is not None:
            opinions = self.saved_opinion_dependencies
        elif cache:
            self.saved_opinion_dependencies = opinion_dependencies
            list(opinion_dependencies)
        if exclude is not None:
            opinion_dependencies = opinion_dependencies.exclude(parent__user=exclude)
        return opinion_dependencies

    def get_collaborators(self, exclude=None):
        """Return a list users that have edited the theory dependency."""
        collaborators = self.collaborators.all()
        if self.created_by is not None and self.created_by not in collaborators:
            self.collaborators.add(self.created_by)
            collaborators = self.collaborators.all()
        if self.modified_by is not None and self.modified_by not in collaborators:
            self.collaborators.add(self.modified_by)
            collaborators = self.collaborators.all()
        if exclude is not None:
            exclude_pk = []
            if isinstance(exclude, list):
                exclude_pk = [x.pk for x in exclude]
            elif isinstance(exclude, User):
                exclude_pk = [exclude.pk]
            collaborators = collaborators.exclude(pk__in=exclude_pk)
        return collaborators

    def get_revisions(self):
        """Return a list revisions pertaining to theory."""
        return Version.objects.get_for_object(self)

    def get_stats(self, stats_type):
        """Return the stats connected to theory.

        Args:
            stats_type (Stats.TYPE or str, optional): The stats sub-type to retrive. Defaults to None.

        Returns:
            Stats or None: The stats object, or none if the query failed.
        """
        # Error checking.
        if not self.assert_theory():
            return None
        # Allow the method to be called with type or slug.
        if isinstance(stats_type, str):
            stats_type = Stats.slug_to_type(stats_type)
        if stats_type is None:
            return None
        if self.saved_stats is not None:
            return self.saved_stats.get(stats_type)
        return get_or_none(self.stats.all(), stats_type=stats_type)

    def get_all_stats(self, cache=False):
        """Return a list of all stats connected to theory, create if necessary."""
        # Error checking.
        if not self.assert_theory():
            return None
        if self.saved_stats is not None:
            return self.saved_stats
        elif cache:
            self.saved_stats = QuerySetDict('stats_type', self.stats.all())
            return self.saved_stats
        else:
            return self.stats.all()

    def add_to_stats(self, opinion, cache=False, save=True):
        for stats in self.get_all_stats(cache=cache):
            if stats.opinion_is_member(opinion):
                stats.add_opinion(opinion, save=save)
            stats.save_changes()

    def remove_from_stats(self, opinion, cache=False, save=True):
        for stats in self.get_all_stats(cache=cache):
            stats.remove_opinion(opinion, save=save)

    def save_stats(self):
        for stats in self.get_all_stats():
            stats.save_changes()

    def reset_stats(self, cache=False, save=True):
        for stats in self.get_all_stats(cache=cache):
            stats.reset(save=save)

    def recalculate_stats(self):
        """Recalculate all stats attached to this theory."""
        # error checking
        if not self.assert_theory(check_dependencies=True):
            return False
        # reset
        self.reset_stats(cache=True, save=False)
        # add
        for opinion in self.get_opinions():
            self.add_to_stats(opinion, cache=True, save=False)
        # save
        self.save_stats()
        return True

    def get_utilization(self, user=None):
        return 0
        if user is None:
            return self.users.exclude(user=user).count()
        return self.users.count()

    def update_hits(self, request):
        hit_count = HitCount.objects.get_for_object(self)
        hit_count_response = HitCountMixin.hit_count(request, hit_count)
        if hit_count_response.hit_counted:
            hit_count.refresh_from_db()
            self.rank = 100 * self.get_opinions().count() + 10 * \
                self.opinion_dependencies.count() + hit_count.hits
            self.save()

    def update_activity_logs(self, user, verb, action_object=None, path=None):
        """Update activity log."""
        # setup
        if path is None:
            path = []
        path.append(self.pk)
        nested_verb = '<# object.a_url {{ object }} #>'
        if verb == 'Created.':
            nested_verb += '*'
        elif verb == 'Deleted.':
            nested_verb = '<strike>' + nested_verb + '</strike>'

        # this activity log
        log = {'sender': user, 'verb': verb, 'action_object': action_object, 'target': self}
        if stream_if_unique(self.target_actions, log):
            # parent dependency
            for parent in self.get_parent_theories():
                if parent.pk not in path:
                    parent.update_activity_logs(user, nested_verb, action_object=self, path=path)

            # categories
            for category in self.categories.all():
                category.update_activity_logs(user, nested_verb, action_object=self)

            # subscribers
            log['verb'] = '<# target.a_url New activity in "{{ target }}" #>.'
            for follower in followers(self):
                if follower != user:
                    log['recipient'] = follower
                    notify_if_unique(follower, log)

    def get_violations(self, is_open=True, is_closed=True, recent=True, expired=True):
        return Violation.get_violations(content=self,
                                        is_open=is_open,
                                        is_closed=is_closed,
                                        recent=recent,
                                        expired=expired)


class Opinion(TheoryPointerBase, models.Model):
    """A container for user opinion data.

    Todo:
        * Remove all auto_now and auto_now_add.
    """
    user = models.ForeignKey(User, related_name='opinions', on_delete=models.CASCADE)
    content = models.ForeignKey(Content, related_name='opinions', on_delete=models.CASCADE)
    pub_date = models.DateField(auto_now_add=True)
    modified_date = models.DateField(auto_now=True)
    anonymous = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)

    force = models.BooleanField(default=False)
    true_input = models.SmallIntegerField(default=0)
    false_input = models.SmallIntegerField(default=0)
    true_total = models.SmallIntegerField(default=0)
    false_total = models.SmallIntegerField(default=0)

    rank = models.SmallIntegerField(default=0)

    class Meta:
        """Where the model options are defined.

        Model metadata is “anything that’s not a field”, such as ordering options (ordering),
        database table name (db_table), or human-readable singular and plural names
        (verbose_name and verbose_name_plural). None are required, and adding class Meta to a
        model is completely optional.

        For more, see: https://docs.djangoproject.com/en/3.0/ref/models/options/
        """
        ordering = ['-rank']
        db_table = 'theories_opinion'
        verbose_name = 'Opinion'
        verbose_name_plural = 'Opinions'
        unique_together = (('content', 'user'),)

    def __str__(self):
        """String method for OpinionDependency."""
        if self.is_true():
            return self.content.get_true_statement()
        else:
            return self.content.get_false_statement()

    def delete(self):
        self.true_input = 0
        self.false_input = 0
        self.true_total = 0
        self.false_total = 0
        self.force = False
        self.deleted = True
        self.save()

        for dependency in self.get_dependencies():
            dependency.delete()

    def is_anonymous(self):
        return self.anonymous or self.user.is_hidden()

    def is_true(self):
        return self.true_points() > self.false_points()

    def is_false(self):
        return not self.is_true()

    def get_owner(self):
        """Return "Anonymous" if owner is hidden, otherwise return user."""
        if self.is_anonymous():
            return 'Anonymous'
        else:
            return self.user.__str__()

    def get_owner_long(self):
        """Return "Anonymous" if owner is hidden, otherwise return user."""
        if self.is_anonymous():
            return 'Anonymous'
        else:
            return self.user.__str__(print_fullname=True)

    def edit_url(self):
        """Return url for editing this opinion."""
        return reverse('theories:opinion-my-editor', kwargs={'content_pk': self.content.pk})

    def compare_url(self, opinion02=None):
        """Return a default url for the compare view of this opinion."""
        if opinion02 is None:
            url = reverse('theories:opinion-compare',
                          kwargs={
                              'content_pk': self.content.pk,
                              'opinion_pk01': self.pk,
                              'opinion_slug02': 'all'
                          })
        elif isinstance(opinion02, Stats):
            url = reverse('theories:opinion-compare',
                          kwargs={
                              'content_pk': self.content.pk,
                              'opinion_pk01': self.pk,
                              'opinion_slug02': opinion02.get_slug()
                          })
        elif isinstance(opinion02, Opinion):
            url = reverse('theories:opinion-compare',
                          kwargs={
                              'content_pk': self.content.pk,
                              'opinion_pk01': self.pk,
                              'opinion_pk02': opinion02.pk
                          })
        else:
            url = ''
        return url

    def get_absolute_url(self):
        """Return the url that views the details of this opinion."""
        return reverse('theories:opinion-detail',
                       kwargs={
                           'content_pk': self.content.pk,
                           'opinion_pk': self.pk
                       })

    def url(self):
        """Return the url that views the details of this opinion."""
        return self.get_absolute_url()

    def get_dependency(self, content, create=False):
        """Return the opinion_dependency for the corresponding content input."""

        # check saved dependencies first
        opinion_dependency = None
        if self.saved_dependencies is not None:
            opinion_dependency = get_or_none(self.saved_dependencies, content=content)

        # make db query
        if opinion_dependency is None:
            if create:
                opinion_dependency, created = self.dependencies.get_or_create(content=content)
            else:
                opinion_dependency = get_or_none(self.dependencies, content=content)

        return opinion_dependency

    def cache(self):
        """Save opinion dependencies."""
        self.get_dependencies(cache=True)

    def get_dependencies(self, cache=False, verbose_level=0):
        """Return opinion dependencies (use cache if available)."""
        # debug
        if verbose_level > 0:
            print("get_dependencies()")
        # get dependencies
        if self.saved_dependencies is not None:
            dependencies = self.saved_dependencies
        elif cache:
            self.saved_dependencies = self.dependencies.all()
            list(self.saved_dependencies)
            dependencies = self.saved_dependencies
        else:
            dependencies = self.dependencies.all()
        # debug
        if verbose_level > 0:
            for dependency in dependencies:
                print("  - %s" % dependency)
        return dependencies

    def get_flat_dependency(self, content, create=True):
        """Return a flat opinion dependency corresponding to the input content.
           This action also populates saved_flat_dependencies, which is a dictionary of
           non-db objects."""
        # setup
        if self.saved_flat_dependencies is None:
            self.get_flat_dependencies()
        # blah
        dependency = self.saved_flat_dependencies.get(content.pk)
        if dependency is None and create:
            dependency = DependencyPointerBase.create(
                parent=self,
                content=content,
            )
            self.saved_flat_dependencies.add(dependency)
        return dependency

    def get_flat_dependencies(self, verbose_level=0):
        """Return a list of non-db objects representing the flattened opinion.
           This action populates saved_flat_dependencies."""

        # debug
        if verbose_level > 0:
            print("get_flat_dependencies()")

        # populate flat dependencies
        if self.saved_flat_dependencies is None:
            # initialize a set of flattened opinion_dependencies
            self.saved_flat_dependencies = QuerySetDict('content.pk')

            # setup intuition
            intuition = self.get_flat_dependency(self.content.get_intuition())

            # evidence
            for evidence in self.get_theory_evidence():
                flat_dependency = self.get_flat_dependency(evidence.content)
                flat_dependency.saved_true_points += evidence.true_percent() * self.true_points()
                flat_dependency.saved_false_points += evidence.false_percent() * \
                    self.false_points()

                # debug
                if verbose_level >= 10:
                    print('\n\n\n')
                    print(1690, '%s: %s' % (self, evidence))
                    print(1691, '  : true_points  = %0.2f' % evidence.true_points())
                    print(1692, '  : false_points = %0.2f' % evidence.false_points())
                    print(
                        1694, '  : tt += %0.2f, tf += %0.2f, ft += %0.2f, ff += %0.2f' % (
                            evidence.true_percent() * self.true_points(),
                            evidence.false_percent() * self.false_points(),
                            0,
                            0,
                        ))

            # sub-theories
            for subtheory in self.get_theory_subtheories():
                subtheory_opinion = subtheory.get_root()
                if subtheory_opinion is not None:
                    for evidence in subtheory_opinion.get_flat_dependencies():

                        # debug
                        if verbose_level >= 10:
                            print('\n\n\n')
                            print(1720, '%s: %s' % (subtheory_opinion, evidence))
                            print(1721, '  : true_points  = %0.2f' % evidence.true_points())
                            print(1722, '  : false_points = %0.2f' % evidence.false_points())
                            print(
                                1724, '  : tt += %0.2f, tf += %0.2f, ft += %0.2f, ff += %0.2f' % (
                                    evidence.true_percent() * subtheory.tt_points(),
                                    evidence.false_percent() * subtheory.tf_points(),
                                    evidence.true_percent() * subtheory.tf_points(),
                                    evidence.false_percent() * subtheory.ff_points(),
                                ))

                        flat_dependency = self.get_flat_dependency(evidence.content)
                        # true_points
                        flat_dependency.saved_true_points += evidence.true_percent() * \
                            subtheory.tt_points()
                        flat_dependency.saved_true_points += evidence.false_percent() * \
                            subtheory.ft_points()

                        # false points
                        flat_dependency.saved_false_points += evidence.true_percent() * \
                            subtheory.tf_points()
                        flat_dependency.saved_false_points += evidence.false_percent() * \
                            subtheory.ff_points()

                # intuition true points
                if subtheory_opinion is None or subtheory_opinion.true_points() == 0:
                    intuition.saved_true_points += subtheory.tt_points()
                    intuition.saved_false_points += subtheory.tf_points()

                    # debug
                    if verbose_level >= 10:
                        print('\n\n\n')
                        print(1740, '%s: %s' % (subtheory, intuition))
                        print(1741, '  : true_points  = %0.2f' % intuition.true_points())
                        print(1742, '  : false_points = %0.2f' % intuition.false_points())
                        print(
                            1744, '  : tt += %0.2f, tf += %0.2f, ft += %0.2f, ff += %0.2f' % (
                                subtheory.tt_points(),
                                subtheory.tf_points(),
                                0,
                                0,
                            ))

                # intuition false points
                if subtheory_opinion is None or subtheory_opinion.false_points() == 0:
                    intuition.saved_true_points += subtheory.ft_points()
                    intuition.saved_false_points += subtheory.ff_points()

                    # debug
                    if verbose_level >= 10:
                        print('\n\n\n')
                        print(1760, '%s: %s' % (subtheory, intuition))
                        print(1761, '  : true_points  = %0.2f' % intuition.true_points())
                        print(1762, '  : false_points = %0.2f' % intuition.false_points())
                        print(
                            1764, '  : tt += %0.2f, tf += %0.2f, ft += %0.2f, ff += %0.2f' % (
                                0,
                                0,
                                subtheory.ft_points(),
                                subtheory.ff_points(),
                            ))

        # debug
        if verbose_level > 0:
            for flat_dependency in self.saved_flat_dependencies:
                print("  - %s" % flat_dependency)

        return self.saved_flat_dependencies

    def get_intuition(self, create=True):
        """Return an opinion dependency for intuition (optionally, create the dependency).
           Additionally, this action adds an intuition dependency to theory.dependencies."""
        content = self.content.get_intuition()
        if create:
            intuition, created = self.dependencies.get_or_create(content=content)
        else:
            intuition = get_or_none(self.get_dependencies(), content=content)
        return intuition

    def get_theory_evidence(self):
        """Returns a query set of the evidence opinion dependencies."""

        return self.dependencies.filter(~Q(content__content_type=Content.TYPE.THEORY) &
                                        ~Q(content__content_type=-Content.TYPE.THEORY))

    def get_theory_subtheories(self):
        """Return all opinion dependencies that point to sub-theories of self.content"""
        return self.dependencies.filter(
            Q(content__content_type=Content.TYPE.THEORY) |
            Q(content__content_type=-Content.TYPE.THEORY))

    def get_parent_opinions(self):
        """Return a query set of opinion dependencies that point to this opinion."""
        return OpinionDependency.objects.filter(parent__user=self.user, content=self.content)

    def update_points(self, verbose_level=0):
        """Use true_input and false_input for opinion and dependencies to update true_points and false_points."""

        # debug
        if verbose_level > 0:
            print("update_points()")

        # count total points
        self.true_total = 0.0
        self.false_total = 0.0
        self.deleted = False
        for dependency in self.get_dependencies():
            true_input = dependency.tt_input + dependency.ft_input
            false_input = dependency.tf_input + dependency.ff_input
            self.true_total += true_input
            self.false_total += false_input
            if true_input == 0 and false_input == 0:
                dependency.delete()
                # debug
                if verbose_level >= 10:
                    print("  delete: %s" % dependency)
            elif verbose_level >= 10:
                print("  %s: true_input = %d, false_input = %d" %
                      (dependency, true_input, false_input))

        # debug
        if verbose_level > 0:
            print("  total input points: true = %d, false = %d" %
                  (self.true_total, self.false_total))

        # intuition
        save_intuition = False
        intuition = self.get_intuition()
        if self.true_input > 0 and self.true_total == 0:
            intuition.tt_input = self.true_input
            self.true_total += self.true_input
            save_intuition = True
        if self.false_input > 0 and self.false_total == 0:
            intuition.tf_input = self.false_input
            self.false_total += self.false_input
            save_intuition = True
        if save_intuition:
            self.content.add_dependency(self.content.get_intuition())
            intuition.save()
        self.save()

    def copy(self, user, recursive=False, path=None, verbose_level=0):
        """Copy opinion to user's opinion"""
        # debug
        if verbose_level > 0:
            print("opinion.copy()")

        # setup
        if path is None:
            path = []
        path.append(self.content.pk)
        theory = self.content

        # delete existing opinion
        user_opinion = get_or_none(theory.get_opinions(), user=user)
        if user_opinion is not None:
            theory.remove_from_stats(user_opinion, cache=True, save=False)
            user_opinion.delete()

        # new opinion
        user_opinion, created = theory.opinions.get_or_create(user=user)
        user_opinion.true_input = self.true_input
        user_opinion.false_input = self.false_input
        user_opinion.force = self.force
        user_opinion.save()

        # populate dependencies
        for opinion_dependency in self.get_dependencies():
            user_dependency, created = OpinionDependency.objects.get_or_create(
                parent=user_opinion,
                content=opinion_dependency.content,
                tt_input=opinion_dependency.tt_input,
                tf_input=opinion_dependency.tf_input,
                ft_input=opinion_dependency.ft_input,
                ff_input=opinion_dependency.ff_input,
            )

        # points
        user_opinion.update_points()

        # recursive
        if recursive:
            for subtheory in self.get_theory_subtheories():
                root_opinion = subtheory.get_root()
                if root_opinion is not None and root_opinion.get_dependency_pk() not in path:
                    root_opinion.copy(user, recursive=True)

        # stats
        theory.add_to_stats(user_opinion, cache=True, save=False)
        theory.save_stats()

        # debug
        if verbose_level > 0:
            print("opinion.copy()")
        return user_opinion

    def true_points(self):
        """Return the total true points for opinion."""
        if self.force:
            total = self.true_input + self.false_input
            if total > 0:
                return self.true_input / total
            else:
                return 0.0
        else:
            total = self.true_total + self.false_total
            if total > 0:
                return self.true_total / total
            else:
                return 0.0

    def false_points(self):
        """Return the total false points for opinion."""
        if self.force:
            total = self.true_input + self.false_input
            if total > 0:
                return self.false_input / total
            else:
                return 0.0
        else:
            total = self.true_total + self.false_total
            if total > 0:
                return self.false_total / total
            else:
                return 0.0

    def swap_true_false(self):
        """Swap the true and false points of the opinion (used when swapping the title of the theory)."""

        # self
        self.true_total, self.false_total = self.false_total, self.true_total
        self.true_input, self.false_input = self.false_input, self.true_input
        self.save()

        # dependencies
        for dependency in self.get_dependencies():
            dependency.tt_input, dependency.tf_input = dependency.tf_input, dependency.tt_input
            dependency.ft_input, dependency.ff_input = dependency.ff_input, dependency.ft_input
            dependency.save()

    def update_hits(self, request):
        hit_count = HitCount.objects.get_for_object(self)
        hit_count_response = HitCountMixin.hit_count(request, hit_count)
        if hit_count_response.hit_counted:
            hit_count.refresh_from_db()
            self.rank = hit_count.hits
            self.save()

    # ToDo: activate when opinion is modified by system
    def update_activity_logs(self, user, verb='Modified', action_object=None):
        """Update activity log."""
        # setup
        system_user = User.get_system_user()

        # this activity log
        log = {
            'sender': system_user,
            'verb': verb,
            'action_object': action_object,
            'target': self
        }  # TODO: might be a bug but the prev diff had action_object = self
        stream_if_unique(self.target_actions, log)

        # subscribed users
        log['verb'] = '<# target.url {{ target.get_owner }} has modified their opinion of "{{ target }}". #>',
        for follower in followers(self):
            if follower != user:
                log['recipient'] = follower
                notify_if_unique(follower, log)

    def is_deleted(self):
        return self.deleted


class OpinionDependency(DependencyPointerBase, models.Model):
    """A container for user opinion dependencies."""

    parent = models.ForeignKey(Opinion, related_name='dependencies', on_delete=models.CASCADE)
    content = models.ForeignKey(Content,
                                related_name='opinion_dependencies',
                                on_delete=models.CASCADE)

    tt_input = models.SmallIntegerField(default=0)
    tf_input = models.SmallIntegerField(default=0)
    ft_input = models.SmallIntegerField(default=0)
    ff_input = models.SmallIntegerField(default=0)

    # Cache attributes
    saved_root_opinion = None

    class Meta:
        """Where the model options are defined.

        Model metadata is “anything that’s not a field”, such as ordering options (ordering),
        database table name (db_table), or human-readable singular and plural names
        (verbose_name and verbose_name_plural). None are required, and adding class Meta to a
        model is completely optional.

        For more, see: https://docs.djangoproject.com/en/3.0/ref/models/options/
        """
        db_table = 'theories_opinion_dependency'
        verbose_name = 'Opinion Dependency'
        verbose_name_plural = 'Opinion Dependencys'
        unique_together = (('content', 'parent'),)

    def get_absolute_url(self):
        """Return a url pointing to the user's opinion of content (not opinion_dependency)."""
        opinion_root = self.get_root()
        if opinion_root is None:
            return None
        elif opinion_root.anonymous == self.parent.anonymous:
            return opinion_root.url()

    def url(self):
        """Return a url pointing to the user's opinion of content (not opinion_dependency)."""
        return self.get_absolute_url()

    def get_root(self):
        """Get the user opinion pointing to content."""
        if self.saved_root_opinion is not None:
            root_opinion = self.saved_root_opinion
        else:
            if self.is_subtheory():
                root_opinion = get_or_none(self.content.opinions, user=self.parent.user)
                self.saved_root_opinion = root_opinion
            else:
                root_opinion = None
        return root_opinion

    def tt_points(self):
        """Returns the percentage of true points (not total points) for the True-True category."""
        if self.parent.true_total > 0:
            return self.tt_input / self.parent.true_total * self.parent.true_points()
        else:
            return 0.0

    def tf_points(self):
        """Returns the percentage of true points (not total points) for the True-True category."""
        if self.parent.false_total > 0:
            return self.tf_input / self.parent.false_total * self.parent.false_points()
        else:
            return 0.0

    def ft_points(self):
        """Returns the percentage of true points (not total points) for the True-True category."""
        if self.parent.true_total > 0:
            return self.ft_input / self.parent.true_total * self.parent.true_points()
        else:
            return 0.0

    def ff_points(self):
        """Returns the percentage of true points (not total points) for the True-True category."""
        if self.parent.false_total > 0:
            return self.ff_input / self.parent.false_total * self.parent.false_points()
        else:
            return 0.0

    def true_points(self):
        return self.tt_points() + self.ft_points()

    def false_points(self):
        return self.tf_points() + self.ff_points()

    def is_deleted(self):
        return not self.parent.content.get_dependencies().filter(pk=self.content.pk).exists()


class Stats(TheoryPointerBase, models.Model):
    """A container for theory statistical data."""

    # Defines
    TYPE = Choices(
        (0, 'ALL', ('All')),
        (1, 'SUPPORTERS', ('Supporters')),
        (2, 'MODERATES', ('Moderates')),
        (3, 'OPPOSERS', ('Opposers')),
    )

    # Variables
    content = models.ForeignKey(Content, related_name='stats', on_delete=models.CASCADE)
    opinions = models.ManyToManyField(Opinion, related_name='stats', blank=True)
    stats_type = models.SmallIntegerField(choices=TYPE)
    total_true_points = models.FloatField(default=0.0)
    total_false_points = models.FloatField(default=0.0)

    class Meta:
        """Where the model options are defined.

        Model metadata is “anything that’s not a field”, such as ordering options (ordering),
        database table name (db_table), or human-readable singular and plural names
        (verbose_name and verbose_name_plural). None are required, and adding class Meta to a
        model is completely optional.

        For more, see: https://docs.djangoproject.com/en/3.0/ref/models/options/
        """
        db_table = 'theories_stats'
        verbose_name = 'Stats'
        verbose_name_plural = 'Stats'
        unique_together = (('content', 'stats_type'),)

    def __str__(self):
        """Return stats_type + title."""
        if self.is_true():
            return self.content.get_true_statement()
        else:
            return self.content.get_false_statement()

    @classmethod
    def initialize(cls, theory):
        """[summary]

        Returns:
            [type]: [description]

        Todo:
            * Fix list(cls.TYPE).
        """
        for stats_type in [x[0] for x in list(cls.TYPE)]:
            stats, created = theory.stats.get_or_create(stats_type=stats_type)

    @classmethod
    def type_to_slug(cls, stats_type):
        """Return the slug used for urls to reference this object."""
        if stats_type == cls.TYPE.ALL:
            return 'all'
        elif stats_type == cls.TYPE.SUPPORTERS:
            return 'supporters'
        elif stats_type == cls.TYPE.MODERATES:
            return 'moderates'
        elif stats_type == cls.TYPE.OPPOSERS:
            return 'opposers'
        else:
            assert False

    @classmethod
    def slug_to_type(cls, slug):
        """Return the type."""
        if slug == 'supporters':
            return cls.TYPE.SUPPORTERS
        if slug == 'moderates':
            return cls.TYPE.MODERATES
        if slug == 'opposers':
            return cls.TYPE.OPPOSERS
        return cls.TYPE.ALL

    def get_slug(self):
        """Return the slug used for urls to reference this object."""
        cls = self.__class__
        return cls.type_to_slug(self.stats_type)

    def get_owner(self, short=False):
        """Return a human readable type of this object."""
        if self.stats_type == self.TYPE.ALL:
            return 'Everyone'
        elif self.stats_type == self.TYPE.SUPPORTERS:
            return 'Supporters'
        elif self.stats_type == self.TYPE.MODERATES:
            return 'Moderates'
        elif self.stats_type == self.TYPE.OPPOSERS:
            return 'Opposers'
        else:
            assert False

    def get_owner_long(self, short=False):
        """Return a human readable possessive type of this object."""
        if self.stats_type == self.TYPE.ALL:
            return "Everyone"
        elif self.stats_type == self.TYPE.SUPPORTERS:
            return "The Supporters'"
        elif self.stats_type == self.TYPE.MODERATES:
            return "The Moderates'"
        elif self.stats_type == self.TYPE.OPPOSERS:
            return "The Opposers'"
        else:
            assert False

    def get_point_range(self):
        """Return the range of true points this object possesses."""
        if self.stats_type == self.TYPE.ALL:
            return 0.000, 1.000
        elif self.stats_type == self.TYPE.SUPPORTERS:
            return 0.666, 1.000
        elif self.stats_type == self.TYPE.MODERATES:
            return 0.333, 0.666
        elif self.stats_type == self.TYPE.OPPOSERS:
            return 0.000, 0.333
        else:
            assert False

    def get_dependency(self, content, create=True):
        """Return the stats dependency for the corresponding content (optionally, create the stats dependency)."""
        # check saved dependencies first
        if self.saved_dependencies is not None and content.pk in self.saved_dependencies:
            return self.saved_dependencies.get(content.pk)
        # make db query
        elif create:
            dependency, created = self.dependencies.get_or_create(content=content)
            if self.saved_dependencies is not None:
                self.saved_dependencies.add(dependency)
            return dependency
        else:
            return get_or_none(self.dependencies, content=content)

    def get_dependencies(self, cache=False):
        """Return the stats dependency for the theory (use cache if available)."""
        if self.saved_dependencies is not None:
            return self.saved_dependencies
        elif cache:
            self.saved_dependencies = QuerySetDict('content.pk')
            for dependency in self.dependencies.all():
                self.saved_dependencies.add(dependency)
            return self.saved_dependencies
        else:
            return self.dependencies.all()

    def get_flat_dependency(self, content, create=True):
        """Return the flat stats dependency for the input content (optionally, create the dependency)."""
        # check saved dependencies first
        if self.saved_flat_dependencies is not None and content.pk in self.saved_flat_dependencies:
            return self.saved_flat_dependencies.get(content.pk)
        # make db query
        elif create:
            dependency, created = self.flat_dependencies.get_or_create(content=content)
            if self.saved_flat_dependencies is not None:
                self.saved_flat_dependencies.add(dependency)
            return dependency
        else:
            return get_or_none(self.flat_dependencies, content=content)

    def get_flat_dependencies(self, cache=False):
        """Return a query set of the flat dependencies/nested evidence (use cache if available)."""
        if self.saved_flat_dependencies is not None:
            return self.saved_flat_dependencies
        elif cache:
            self.saved_flat_dependencies = QuerySetDict('content.pk')
            for dependency in self.flat_dependencies.all():
                self.saved_flat_dependencies.add(dependency)
            return self.saved_flat_dependencies
        else:
            return self.flat_dependencies.all()

    def add_opinion(self, opinion, save=True):
        if self.opinion_is_member(opinion):

            # root
            self.total_true_points += opinion.true_points()
            self.total_false_points += opinion.false_points()
            if save:
                self.save()
            else:
                self.altered = True

            # dependencies
            for opinion_dependency in opinion.get_dependencies():
                stats_dependency = self.get_dependency(content=opinion_dependency.content)
                stats_dependency.total_true_points += opinion_dependency.true_points()
                stats_dependency.total_false_points += opinion_dependency.false_points()
                if save:
                    stats_dependency.save()
                else:
                    stats_dependency.altered = True

            # flat_dependencies
            for flat_opinion_dependency in opinion.get_flat_dependencies():
                flat_stats_dependency = self.get_flat_dependency(
                    content=flat_opinion_dependency.content)
                flat_stats_dependency.total_true_points += flat_opinion_dependency.true_points()
                flat_stats_dependency.total_false_points += flat_opinion_dependency.false_points()
                if save:
                    flat_stats_dependency.save()
                else:
                    flat_stats_dependency.altered = True

            # add
            self.opinions.add(opinion)

    def remove_opinion(self, opinion, save=True):
        if self.opinions.filter(pk=opinion.pk).exists():

            # root
            self.total_true_points -= opinion.true_points()
            self.total_false_points -= opinion.false_points()
            if save:
                self.save()
            else:
                self.altered = True

            # Update stats.
            for opinion_dependency in opinion.get_dependencies():
                stats_dependency = self.get_dependency(content=opinion_dependency.content)
                stats_dependency.total_true_points -= opinion_dependency.true_points()
                stats_dependency.total_false_points -= opinion_dependency.false_points()
                if save:
                    stats_dependency.save()
                else:
                    stats_dependency.altered = True

            # Update flat stats.
            for flat_opinion_dependency in opinion.get_flat_dependencies():
                flat_stats_dependency = self.get_flat_dependency(
                    content=flat_opinion_dependency.content)
                flat_stats_dependency.total_true_points -= flat_opinion_dependency.true_points()
                flat_stats_dependency.total_false_points -= flat_opinion_dependency.false_points()
                if save:
                    flat_stats_dependency.save()
                else:
                    flat_stats_dependency.altered = True

            # remove
            self.opinions.remove(opinion)

    def get_opinions(self):
        """Return a query set of all opinions that meet the stats category's criterion."""
        return self.opinions.filter(deleted=False)

    def get_absolute_url(self):
        return self.opinion_url()

    def url(self):
        """Return the url for viewing the details of this object (opinion-details)."""
        return self.get_absolute_url()

    def opinion_url(self):
        return reverse('theories:opinion-detail',
                       kwargs={
                           'content_pk': self.get_dependency_pk(),
                           'opinion_slug': self.get_slug()
                       })

    def opinions_url(self):
        return reverse("theories:opinion-index",
                       kwargs={
                           'content_pk': self.content.pk,
                           'opinion_slug': self.get_slug()
                       })

    def compare_url(self, opinion02=None):
        """Return a url to compare this object with a default object (opinion-compare)."""
        if opinion02 is None:
            url = reverse('theories:opinion-compare',
                          kwargs={
                              'content_pk': self.content.pk,
                              'opinion_slug01': self.get_slug(),
                              'opinion_slug02': 'moderates'
                          })
        elif isinstance(opinion02, Stats):
            url = reverse('theories:opinion-compare',
                          kwargs={
                              'content_pk': self.content.pk,
                              'opinion_slug01': self.get_slug(),
                              'opinion_slug02': opinion02.get_slug()
                          })
        elif isinstance(opinion02, Opinion):
            url = reverse('theories:opinion-compare',
                          kwargs={
                              'content_pk': self.content.pk,
                              'opinion_slug01': self.get_slug(),
                              'opinion_pk02': opinion02.pk
                          })
        else:
            url = ''
        return url

    def opinion_is_member(self, opinion):
        """Test whether or not the opinion meets the criterion of the stat categorization."""
        if opinion.true_points() + opinion.false_points() == 0:
            return False
        elif self.stats_type == self.TYPE.ALL:
            return True
        elif self.stats_type == self.TYPE.SUPPORTERS and opinion.true_points() >= 0.666:
            return True
        elif self.stats_type == self.TYPE.MODERATES and opinion.true_points(
        ) < 0.666 and opinion.false_points() < 0.666:
            return True
        elif self.stats_type == self.TYPE.OPPOSERS and opinion.false_points() >= 0.666:
            return True
        else:
            return False

    def cache(self, lazy=False):
        """Save regular and flat dependency queries for the purpose of db efficiency."""
        if lazy:
            self.saved_dependencies = QuerySetDict('content.pk')
            self.saved_flat_dependencies = QuerySetDict('content.pk')
        else:
            self.get_dependencies(cache=True)
            self.get_flat_dependencies(cache=True)

    def true_points(self):
        """Returns true points (a percentage of total)."""
        if self.total_points() > 0:
            return self.total_true_points / self.total_points()
        else:
            return 0.0

    def false_points(self):
        """Returns false points (a percentage of total)."""
        if self.total_points() > 0:
            return self.total_false_points / self.total_points()
        else:
            return 0.0

    def total_points(self):
        """Returns total opinion points awarded to this theory."""
        return self.total_true_points + self.total_false_points

    def num_supporters(self):
        """Returns the number of supporters."""
        return round(self.true_points() * self.opinions.count())

    def num_opposers(self):
        """Returns the number of opposers."""
        return round(self.false_points() * self.opinions.count())

    def reset(self, save=True):
        """Reset this objects points as well as all dependency points."""
        # reset self
        self.total_true_points = 0.0
        self.total_false_points = 0.0
        # reset theory dependencies
        for stats_dependency in self.get_dependencies():
            stats_dependency.reset(save=save)
        # reset theory flat dependencies
        for stats_flat_dependency in self.get_flat_dependencies():
            stats_flat_dependency.reset(save=save)
        # opinions
        self.opinions.clear()
        if save:
            self.save()
        else:
            self.altered = True

    def save_changes(self):
        """Save changes to all dependencies."""
        # self
        if self.altered:
            self.altered = False
            self.save()

        # dependencies
        if self.saved_dependencies is not None:
            for dependency in self.get_dependencies():
                if dependency.altered:
                    dependency.altered = False
                    dependency.save()

        # flat_dependencies
        if self.saved_flat_dependencies is not None:
            for flat_dependency in self.get_flat_dependencies():
                if flat_dependency.altered:
                    flat_dependency.altered = False
                    flat_dependency.save()

    def swap_true_false(self):
        """Swap the true and false points."""

        # self
        self.total_true_points, self.total_false_points = self.total_false_points, self.total_true_points
        self.save()

        # dependencies
        for dependency in self.get_dependencies():
            dependency.total_true_points, dependency.total_false_points = dependency.total_false_points, dependency.total_true_points
            dependency.save()

        # flat dependencies
        for dependency in self.get_flat_dependencies():
            dependency.total_true_points, dependency.total_false_points = dependency.total_false_points, dependency.total_true_points
            dependency.save()


class StatsDependency(DependencyPointerBase, models.Model):
    """A container for dependency based statistics.

    Attributes:
        parent (Stats): The parent statistic for the dependency (the parent dependency will be a theory
            or sub-theory).
        content (Content): The dependency (theory, sub-theory, or evidence) that this stat
            pertains to.
        total_true_points (double): Total number of true points awared to the dependency (each user
            has a total of 1.0 points to distribute to theories/dependencies).
        total_false_points (double): Total number of false points awared to the dependency (each user
            has a total of 1.0 points to distribute to theories/dependencies).
    """
    parent = models.ForeignKey(Stats, related_name='dependencies', on_delete=models.CASCADE)
    content = models.ForeignKey(Content,
                                related_name='stats_dependencies',
                                on_delete=models.CASCADE)
    total_true_points = models.FloatField(default=0.0)
    total_false_points = models.FloatField(default=0.0)

    class Meta:
        """Where the model options are defined.

        Model metadata is “anything that’s not a field”, such as ordering options (ordering),
        database table name (db_table), or human-readable singular and plural names
        (verbose_name and verbose_name_plural). None are required, and adding class Meta to a
        model is completely optional.

        For more, see: https://docs.djangoproject.com/en/3.0/ref/models/options/
        """
        db_table = 'theories_stats_dependency'
        verbose_name = 'Stats Dependency'
        verbose_name_plural = 'Stats Dependency'
        unique_together = (('content', 'parent'),)

    def url(self):
        """Return a url pointing to content's root (not dependency)."""
        root = self.get_root()
        if root is None:
            return None
        else:
            return root.url()

    def get_root(self):
        """Get the root stats pointing to content."""
        return get_or_none(self.content.stats, stats_type=self.parent.stats_type)

    def true_points(self):
        """Returns true points (a percentage of total)."""
        if self.parent.total_points() > 0:
            return self.total_true_points / self.parent.total_points()
        else:
            return 0.0

    def false_points(self):
        """Returns false points (a percentage of total)."""
        if self.parent.total_points() > 0:
            return self.total_false_points / self.parent.total_points()
        else:
            return 0.0

    def total_points(self):
        """Returns total points (a percentage of total)."""
        if self.parent.total_points() > 0:
            return (self.total_true_points + self.total_false_points) / self.parent.total_points()
        else:
            return 0.0

    def reset(self, save=True):
        """Zero the true and false points (optionally, do not save results)."""
        self.total_true_points = 0.0
        self.total_false_points = 0.0
        if save:
            self.save()
        else:
            self.altered = True


class StatsFlatDependency(DependencyPointerBase, models.Model):
    """A container for flat dependency (nested evidence) statistics"""
    parent = models.ForeignKey(Stats, related_name='flat_dependencies', on_delete=models.CASCADE)
    content = models.ForeignKey(Content,
                                related_name='stats_flat_dependencies',
                                on_delete=models.CASCADE)
    total_true_points = models.FloatField(default=0.0)
    total_false_points = models.FloatField(default=0.0)

    class Meta:
        """Where the model options are defined.

        Model metadata is “anything that’s not a field”, such as ordering options (ordering),
        database table name (db_table), or human-readable singular and plural names
        (verbose_name and verbose_name_plural). None are required, and adding class Meta to a
        model is completely optional.

        For more, see: https://docs.djangoproject.com/en/3.0/ref/models/options/
        """
        db_table = 'theories_stats_flat_dependency'
        verbose_name = 'Stats Flat Dependency'
        verbose_name_plural = 'Stats Flat Dependencys'
        unique_together = (('content', 'parent'),)

    def url(self):
        """Return a url pointing to content's root (not dependency).

        Returns:
            str: [description]
        """
        root = self.get_root()
        if root is None:
            return None
        else:
            return root.url()

    def get_root(self):
        """Get the root stats pointing to content.

        Returns:
            [type]: [description]
        """
        return get_or_none(self.content.stats, stats_type=self.parent.stats_type)

    def true_points(self):
        """Todo

        Returns:
            [type]: [description]
        """
        if self.parent.total_points() > 0:
            return self.total_true_points / self.parent.total_points()
        else:
            return 0.0

    def false_points(self):
        """Todo

        Returns:
            [type]: [description]
        """
        if self.parent.total_points() > 0:
            return self.total_false_points / self.parent.total_points()
        else:
            return 0.0

    def total_points(self):
        """Returns the total points awarded to this dependency (a percentage of total).

        Returns:
            float: The points.
        """
        return self.true_points() + self.false_points()

    def reset(self, save=True):
        """Zero the true and false points.

        Args:
            save (bool, optional): If true, the changes are saved to the database.
                Defaults to True.
        """
        self.total_true_points = 0.0
        self.total_false_points = 0.0
        if save:
            self.save()
        else:
            self.altered = True
