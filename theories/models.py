"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       theories/models.py
@brief      A collection of models for the app
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# imports
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

from reversion.models import Version
from actstream import action
from actstream.models import followers
from actstream.actions import is_following
from notifications.signals import notify

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Sum, F, Q
from django.template.defaultfilters import slugify
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation
from model_utils import Choices

from hitcount.models import HitCount
from hitcount.views import HitCountMixin

from users.models import User, Violation
from core.utils import *


# *******************************************************************************
# defines
# *******************************************************************************
DEBUG = False
logger = logging.getLogger('django')


# *******************************************************************************
# Helper Classes
#
#
#
#
#
#
#
#
# *******************************************************************************


# ************************************************************
# QuerySetDict
# ************************************************************
class QuerySetDict():

    # ******************************
    # QuerySetDict
    # ******************************
    def __init__(self, attrib_key, queryset=None):
        self.dict = {}
        self.attrib_key = attrib_key
        if queryset is not None:
            for x in queryset:
                self.dict[self.get_key(x)] = x

    # ******************************
    # QuerySetDict
    # ******************************
    def __iter__(self):
        self.dict_iter = self.dict.values().__iter__()
        return self

    # ******************************
    # QuerySetDict
    # ******************************
    def __next__(self):
        return self.dict_iter.__next__()

    # ******************************
    # QuerySetDict
    # ******************************
    def __str__(self):
        return str(list(self))

    # ******************************
    # QuerySetDict
    # ******************************
    def get_key(self, obj):
        key = obj
        for key_str in self.attrib_key.split('.'):
            key = getattr(key, key_str)
        return key

    # ******************************
    # QuerySetDict
    # ******************************
    def add(self, x):
        self.dict[self.get_key(x)] = x

    # ******************************
    # QuerySetDict
    # ******************************
    def get(self, key):
        if key in self.dict.keys():
            return self.dict[key]
        else:
            return None

    # ******************************
    # QuerySetDict
    # ******************************
    def count(self):
        return len(self.dict)


# *******************************************************************************
# Theory Classes
#
#
#
#
#
#
#
#
# *******************************************************************************


# ************************************************************
# Category
# ************************************************************
class Category(models.Model):
    """A container for categories."""
    title = models.CharField(max_length=50)
    slug = models.SlugField()
    deleted_theories = models.ManyToManyField(
        'TheoryNode', related_name='old_categories', symmetrical=False, blank=True)

    # ******************************
    # Category
    # ******************************
    class Meta:
        db_table = 'theories_category'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    # ******************************
    # Category
    # ******************************
    def __str__(self):
        """Returns the category's title."""
        return self.title

    # ******************************
    # Category
    # ******************************
    def save(self, *args, **kwargs):
        """Automatically adds the slug."""
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    # ******************************
    # Category
    # ******************************
    @classmethod
    def get(cls, title, create=False):
        """Return category model with matching title, get_or_create category if the create flag is true."""
        slug = slugify(title)
        if create:
            category, created = cls.objects.get_or_create(slug=slug)
        else:
            category = get_or_none(cls.objects, slug=slug)
        return category

    # ******************************
    # Category
    # ******************************
    @classmethod
    def get_all(cls, exclude=[]):
        """Get all categories not in exclude list."""
        exclude_slugs = [slugify(x) for x in exclude]
        return cls.objects.exclude(slug__in=exclude_slugs).annotate(nTheories=Count('theories')).order_by('-nTheories')

    # ******************************
    # Category
    # ******************************
    def get_absolute_url(self):
        """Return the url for viewing all theories within category."""
        return reverse('theories:theories', kwargs={'cat': self.slug})

    # ******************************
    # Category
    # ******************************
    def url(self):
        """Return the url for viewing all theories within category."""
        return self.get_absolute_url()

    # ******************************
    # Category
    # ******************************
    def activity_url(self):
        """Returns the action url for viewing the categories's activity feed."""
        return reverse('theories:activity', kwargs={'cat': self.slug})

    # ******************************
    # Category
    # ******************************
    def get_theories(self):
        """Return all theories within category."""
        return self.theories.all()

    # ******************************
    # Category
    # ******************************
    def update_activity_logs(self, user, verb, action_object=None):
        """Update activity log."""

        # this activity log
        log = {'sender':user, 'verb':verb, 'action_object':action_object, 'target':self}
        stream_if_unique(self.target_actions, log)

        # subscribers
        for follower in followers(self):
            if follower != user:
                log['recipient'] = follower
                notify_if_unique(follower, log)


# ************************************************************
# TheoryNode
# ************************************************************
@reversion.register(fields=['node_type', 'title00', 'title01', 'details'])
class TheoryNode(models.Model):
    """A container for theory, evidence, and sub-theory data."""

    TYPE = Choices(
        (10, 'THEORY', ('Theory')),
        (20, 'EVIDENCE', ('Evidence (other)')),
        (21, 'FACT', ('Evidence (fact)')),
        (-10, 'DELETED_THEORY', ('Deleted Theory')),
        (-20, 'DELETED_EVIDENCE', ('Deleted Evidence (other)')),
        (-21, 'DELETED_FACT', ('Deleted Evidence (fact)')),
    )

    # Variables
    INTUITION_PK = 1

    node_type = models.SmallIntegerField(choices=TYPE)
    title00 = models.CharField(max_length=255, blank=True, null=True)
    title01 = models.CharField(max_length=255, unique=True)
    details = models.TextField(max_length=10000, blank=True)
    categories = models.ManyToManyField(
        Category, related_name='theories', blank=True)

    pub_date = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, models.SET_NULL, related_name='created_nodes', blank=True, null=True)
    modified_by = models.ForeignKey(
        User, models.SET_NULL, related_name='edited_nodes', blank=True, null=True)
    modified_date = models.DateTimeField(
        models.SET_NULL, blank=True, null=True)

    utilization = models.IntegerField(default=0)
    rank = models.SmallIntegerField(default=0)
    nodes = models.ManyToManyField(
        'self', related_name='parent_nodes', symmetrical=False, blank=True)
    flat_nodes = models.ManyToManyField(
        'self', related_name='parent_flat_nodes', symmetrical=False, blank=True)

    violations = GenericRelation(Violation)

    # ******************************
    # TheoryNode
    # ******************************
    class Meta:
        ordering = ['-rank']
        db_table = 'theories_theory_node'
        verbose_name = 'Theory Node'
        verbose_name_plural = 'Theory Nodes'
        permissions = (
            ('swap_title', 'Can swap true/false title.'),
            ('change_title', 'Can change title.'),
            ('change_details', 'Can change details.'),
            ('delete_reversion', 'Can delete revision.'),
            ('merge_theorynode', 'Can merge nodes.'),
            ('backup_theorynode', 'Can create backup.'),
            ('remove_theorynode', 'Can remove Theory Node.'),
            ('restore_theorynode', 'Can restore/revert from revision.'),
            ('convert_theorynode', 'Can convert theory <=> evidence.'),
        )

    # ******************************
    # TheoryNode
    # ******************************
    @classmethod
    def get_demo(cls):
        """Generator to create a demo theory with sub-theories and evidence."""
        theory = cls.get_or_create_theory(true_title='Demo Theory')
        subtheory = theory.get_or_create_subtheory(
            true_title='Demo Sub-Theory')
        fact = theory.get_or_create_evidence(title='Demo Fact', fact=True)
        intuition = theory.get_or_create_evidence(title='Demo Intuition')
        return theory

    # ******************************
    # TheoryNode
    # ******************************
    @classmethod
    def get_or_create_theory(cls, true_title, false_title=None, created_by=None, category='all'):
        """Generator to translate true_title input and etc to class variables."""
        kwargs = {'node_type': cls.TYPE.THEORY, 'title01': true_title}
        if false_title is not None:
            kwargs['title00'] = false_title
        if created_by is not None:
            kwargs['created_by'] = created_by
            kwargs['modified_by'] = created_by
        theory, created = cls.objects.get_or_create(**kwargs)
        theory.categories.add(Category.get(category))
        return theory

    # ******************************
    # TheoryNode
    # ******************************
    def get_or_create_subtheory(self, true_title, false_title=None, created_by=None):
        """Generator to translate true_title input and etc to class variables."""
        # error checking
        if not self.assert_theory():
            return None
        cls = self.__class__
        kwargs = {'node_type': cls.TYPE.THEORY, 'title01': true_title}
        if false_title is not None:
            kwargs['title00'] = false_title
        if created_by is not None:
            kwargs['created_by'] = created_by
            kwargs['modified_by'] = created_by
        subtheory, created = cls.objects.get_or_create(**kwargs)
        self.add_node(subtheory)
        return subtheory

    # ******************************
    # TheoryNode
    # ******************************
    def get_or_create_evidence(self, title, created_by=None, fact=False):
        """Generator to translate title input and etc to class variables."""
        # error checking
        if not self.assert_theory():
            return None
        cls = self.__class__
        kwargs = {'node_type': cls.TYPE.EVIDENCE, 'title01': title}
        if fact:
            kwargs['node_type'] = self.TYPE.FACT
        if created_by is not None:
            kwargs['created_by'] = created_by
            kwargs['modified_by'] = created_by
        evidence, created = cls.objects.get_or_create(**kwargs)
        self.add_node(evidence)
        return evidence

    # ******************************
    # TheoryNode
    # ******************************
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

    # ******************************
    # TheoryNode
    # ******************************
    def get_title(self):
        self.assert_evidence()
        return self.title01

    # ******************************
    # TheoryNode
    # ******************************
    def get_true_statement(self):
        self.assert_theory()
        return self.title01

    # ******************************
    # TheoryNode
    # ******************************
    def get_false_statement(self):
        self.assert_theory()
        if self.title00 is None or self.title00 == '':
            return '%s, is false.' % self.title01.strip('.')
        else:
            return self.title00

    # ******************************
    # TheoryNode
    # ******************************
    def about(self):
        """Returns a string with a title and details."""
        return '%s\n\n%s' % (self.title01, self.details)

    # ******************************
    # TheoryNode
    # ******************************
    def get_absolute_url(self):
        """Returns the url for viewing the object's details."""
        if self.is_theory():
            return reverse('theories:theory-detail', kwargs={'pk': self.pk})
        else:
            return reverse('theories:evidence-detail', kwargs={'pk': self.pk})

    # ******************************
    # TheoryNode
    # ******************************
    def url(self):
        """Returns the url for viewing the object's details."""
        return self.get_absolute_url()

    # ******************************
    # TheoryNode
    # ******************************
    def activity_url(self):
        """Returns the action url for viewing the object's activity feed."""
        if self.is_theory():
            return reverse('theories:theory-activity', kwargs={'pk': self.pk})
        else:
            return reverse('theories:evidence-activity', kwargs={'pk': self.pk})

    # ******************************
    # TheoryNode
    # ******************************
    def tag_id(self):
        """Returns a unique id string used for html visibility tags."""
        return 'TN%03d' % self.pk

    # ******************************
    # TheoryNode
    # ******************************
    def is_deleted(self):
        """Returns true if node is a theory."""
        return self.node_type < 0

    # ******************************
    # TheoryNode
    # ******************************
    def is_root(self):
        """Returns true if node is a theory and in a category."""
        self.assert_theory()
        return self.categories.count() > 0

    # ******************************
    # TheoryNode
    # ******************************
    def is_theory(self):
        """Returns true if node is a theory."""
        return abs(self.node_type) == self.TYPE.THEORY

    # ******************************
    # TheoryNode
    # ******************************
    def is_subtheory(self):
        """Returns true if node is a theory."""
        return self.is_theory()

    # ******************************
    # TheoryNode
    # ******************************
    def is_evidence(self):
        """Returns true if node is evidence."""
        return abs(self.node_type) == self.TYPE.FACT or abs(self.node_type) == self.TYPE.EVIDENCE

    # ******************************
    # TheoryNode
    # ******************************
    def is_fact(self):
        """Returns true if node is factual evidence (verifiable)."""
        self.assert_evidence()
        return self.is_verifiable()

    # ******************************
    # TheoryNode
    # ******************************
    def is_verifiable(self):
        """Returns true if node is factual evidence (verifiable)."""
        self.assert_evidence()
        return abs(self.node_type) == self.TYPE.FACT

    # ******************************
    # TheoryNode
    # ******************************
    def assert_theory(self, check_nodes=False):
        if self.is_evidence():
            stack01 = inspect.stack()[1]
            stack02 = inspect.stack()[2]
            error = 'Error (%s): This node should not be evidence (pk=%d).\n' % (
                timezone.now().strftime("%Y-%m-%d %X"), self.pk)
            error += '  Traceback[1]: %s, %d, %s, %s \n' % (stack01[1].split(
                'code')[-1], stack01[2], stack01[3], stack01[4][0].strip())
            error += '  Traceback[2]: %s, %d, %s, %s \n' % (stack02[1].split(
                'code')[-1], stack02[2], stack02[3], stack02[4][0].strip())
            logger.error(error)
            if self.nodes.count() > 0:
                logger.error(
                    '842: This node should not have nodes (pk=%d).' % self.pk)
            if self.flat_nodes.count() > 0:
                logger.error(
                    '844: This node should not have flat nodes (pk=%d).' % self.pk)
            return False
        elif check_nodes:
            if self.flat_nodes.filter(node_type__lt=0).exists():
                logger.error(
                    '846: There should not be any flat deleted nodes (pk=%d).' % self.pk)
                return False
        return True

    # ******************************
    # TheoryNode
    # ******************************
    def assert_evidence(self, check_nodes=False):
        if self.is_theory():
            stack01 = inspect.stack()[1]
            stack02 = inspect.stack()[2]
            error = 'Error: This node should not be a theory (pk=%d).\n' % self.pk
            error += '  Traceback[1]: %s, %d, %s, %s \n' % (stack01[1].split(
                'code')[-1], stack01[2], stack01[3], stack01[4][0].strip())
            error += '  Traceback[2]: %s, %d, %s, %s \n' % (stack02[1].split(
                'code')[-1], stack02[2], stack02[3], stack02[4][0].strip())
            logger.error(error)
            return False
        elif check_nodes:
            if self.nodes.count() > 0:
                logger.error(
                    '592: This node should not have nodes (pk=%d).' % self.pk)
                return False
            if self.flat_nodes.count() > 0:
                logger.error(
                    '593: This node should not have flat nodes (pk=%d).' % self.pk)
                return False
        return True

    # ******************************
    # TheoryNode
    # ******************************
    def save(self, user=None, *args, **kwargs):
        """Automatically adds stats and intuition nodes."""
        if user is not None:
            self.modified_by = user
            self.modified_date = timezone.now()
            if self.pk is None:
                self.created_by = user
                self.pub_date = timezone.now()
        super().save(*args, **kwargs)
        if self.is_theory():
            Stats.initialize(self)
            self.flat_nodes.add(self.get_intuition_node())
        return self

    # ******************************
    # TheoryNode
      # Todo: do not save if datetime matches
    # ******************************
    def autosave(self, user, force=False, *args, **kwargs):
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

    # ******************************
    # TheoryNode
    # ******************************
    def save_snapshot(self, user, *args, **kwargs):
        """Create a snapshot of the title(s) and details."""
        # get and delete user's previous snapshots
        for revision in self.get_revisions().filter(revision__user=user, revision__comment='Snapshot'):
            revision.delete()
        # create new snapshot
        with reversion.create_revision():
            super().save(*args, **kwargs)
            reversion.set_user(user)
            reversion.set_comment('Snapshot')

    # ******************************
    # TheoryNode
      # ToDo: improve stats calculation
      # ToDo: add assert
    # ******************************
    def swap_titles(self, user=None):
        """Swap true false titles of theory and permeate the changes to opinions and stats."""
        # error checking
        if not self.assert_theory():
            return False
        # setup
        if user is None:
            user = User.get_system_user()
        # theory node
        self.title00, self.title01 = self.title01, self.title00
        self.save()
        # opinions
        for opinion in self.get_opinions():
            opinion.swap_true_false()
            notify.send(
                sender=user,
                recipient=opinion.user,
                verb="""<# object.url The theory, "{{ object }}" has had its true and false titles swapped. #>""",
                description='This should not effect your <# target.url opinion #> in anyway.',
                action_object=self,
                target=opinion,
                level='warning',
            )
        # stats
        for stats in self.get_all_stats():
            stats.swap_true_false()
        return True

    # ******************************
    # TheoryNode
    # Todo: allow evidence to have user opinions but not editable ones
    # ToDo: go over notification logic
    # ******************************
    def convert(self, user=None, verifiable=False):
        # setup
        if user is None:
            user = User.get_system_user()
        if self.is_theory():
            # error checking
            if self.parent_nodes.count() == 0 or self.is_root():
                logger.error(
                    '461: Cannot convert a root theory to evidence (pk=%d).' % self.pk)
                return False
            # inherit nodes
            for parent_theory in self.get_parent_nodes():
                for theory_node in self.get_nodes():
                    parent_theory.add_node(theory_node)
            # clear stats
            for stats in self.get_all_stats():
                stats.delete()
            # convert theory node
            if verifiable:
                self.node_type = self.TYPE.FACT
            else:
                self.node_type = self.TYPE.EVIDENCE
            self.nodes.clear()
            self.flat_nodes.clear()
        else:
            self.node_type = self.TYPE.THEORY
        self.save(user)
        # notifications (opinions)
        if self.is_theory():
            for opinion in self.get_opinions():
                notify.send(
                    sender=user,
                    recipient=opinion.user,
                    verb='<# object.url The theory, "{{ object }}" has been converted to evidence. #>',
                    description='This change has rendered your <# target.url opinion #> unnecessary.',
                    action_object=self,
                    target=opinion,
                    level='warning',
                )
        # notifications (opinion_nodes)
        for opinion in Opinion.objects.filter(nodes__theory_node__pk=self.pk):
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

    # ******************************
    # TheoryNode
    # ToDo: delete stats
    # ******************************
    def merge(self, theory_node, user=None):
        """Merge this theory node with another, by absorbing the other node."""
        # error checking
        if self.node_type != theory_node.node_type:
            logger.error('496: Cannot merge theory nodes of different type (pk01=%d, pk02=%d).' % (
                self.pk, theory_node.pk))
            return False
        # setup
        if user is None:
            user = User.get_system_user()
        # theories
        if self.is_theory():
            # nodes
            nodes = theory_node.get_nodes().exclude(pk=self.pk)
            flat_nodes = theory_node.get_flat_nodes().exclude(pk=self.pk)
            self.nodes.add(*nodes)
            self.flat_nodes.add(*flat_nodes)
            # opinions
            for opinion02 in theory_node.get_opinions():
                opinion01 = get_or_none(
                    self.get_opinions(), user=opinion02.user)
                if opinion01 is None:
                    theory = opinion02.theory
                    theory.remove_from_stats(opinion02, cache=True, save=False)
                    opinion02.theory = self
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
                    notify_if_unique(opinion02.user, log) # TODO: might be a bug, should it be opinion01.user?
            # stats
            theory_node.save_stats()
            self.save_stats()
        # parent nodes
        for parent_node in theory_node.parent_nodes.filter(~Q(pk=self.pk)):
            parent_node.add_node(self)
        # opinion nodes
        changed_theories = []
        for opinion_node02 in theory_node.opinion_nodes.all():
            opinion = opinion_node02.parent
            opinion_node01 = get_or_none(opinion.get_nodes(), theory_node=self)
            if opinion_node01 is None:
                theory = opinion.theory
                theory.remove_from_stats(opinion, cache=True, save=False)
                opinion_node02.theory_node = self
                opinion_node02.save()
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
        theory_node.delete(user)
        return True

    # ******************************
    # TheoryNode
    # ToDo: reset cache
    # ******************************
    def delete(self, user=None, soft=True):
        """Recursively deletes abandoned nodes."""
        # error checking
        if self.pk == self.INTUITION_PK:
            logger.error(
                '720: Intuition node should not be deleted (pk=%d).' % self.pk)
            return False
        if self.is_deleted():
            logger.error(
                '721: Theory node is already deleted (pk=%d).' % self.pk)
            return False
        # setup
        if user is None:
            user = User.get_system_user()
        # delete
        self.node_type = -abs(self.node_type)
        # save
        if soft:
            self.save(user)
        else:
            super().delete()
        # recursive delete
        if self.is_theory():
            # cleanup evidence
            for evidence in self.get_evidence_nodes():
                if evidence.get_parent_nodes().count() == 0:
                    evidence.delete(user, soft)
            # cleanup sub-theories
            for subtheory in self.get_subtheory_nodes():
                if not subtheory.is_root() and subtheory.get_parent_nodes().count() == 0:
                    subtheory.delete(user, soft)
        # remove flat nodes
        if soft:
            self.parent_flat_nodes.clear()
            for parent_node in self.get_parent_nodes():
                if self.is_theory():
                    exclude_list = list(parent_node.get_nodes().values_list(
                        'pk', flat=True)) + [self.INTUITION_PK]
                    nested_nodes = self.get_nested_nodes().exclude(pk__in=exclude_list)
                    for theory_node in nested_nodes:
                        parent_node.remove_flat_node(theory_node)
            # notifications (opinion)
            if self.is_theory():
                for opinion in self.get_opinions():
                    notify.send(
                        sender=user,
                        recipient=opinion.user,
                        verb='<# object.url {{ object }} has been deleted. #>',
                        description='This change means that your <# target.url opinion #> of {{ target }} is no longer valid.',
                        action_object=self,
                        target=opinion,
                        level='warning',
                    )
            # notifications (opinion_node)
            for opinion in Opinion.objects.filter(nodes__theory_node__pk=self.pk):
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

    # ******************************
    # TheoryNode
    # ******************************
    def cache(self, nodes=True, flat_nodes=True, stats=False):
        """Cache sub-theory and evidence nodes to save on db calls."""
        # error checking
        if not self.assert_theory():
            return False
        if nodes:
            self.get_nodes(cache=True)
        if flat_nodes:
            self.get_flat_nodes(cache=True)
        if stats:
            self.get_all_stats(cache=True)
        return True

    # ******************************
    # TheoryNode
    # ******************************
    def add_node(self, theory_node):
        """Add evidence or a sub-theory to this theory and update the flat nodes."""
        if not self.assert_theory():
            return False
        self.add_nodes([theory_node])
        return True

    # ******************************
    # TheoryNode
    # ******************************
    def add_nodes(self, theory_nodes):
        """Add evidence or a sub-theory to this theory and update the flat nodes."""
        # error checking
        if not self.assert_theory():
            return False
        # nested nodes
        nested_flat_nodes = []
        for theory_node in theory_nodes:
            if theory_node.is_subtheory():
                nested_flat_nodes += list(theory_node.get_nested_nodes())
        # self
        self.nodes.add(*theory_nodes)
        self.flat_nodes.add(*theory_nodes, *nested_flat_nodes)
        # parent nodes
        for parent_node in self.climb_theory_nodes():
            parent_node.flat_nodes.add(*theory_nodes, *nested_flat_nodes)
        return True

    # ******************************
    # TheoryNode
    # ******************************
    def remove_node(self, theory_node, user=None):
        # error checking
        if not self.assert_theory(check_nodes=True):
            return False
        # setup
        if user is None:
            user = User.get_system_user()
        # remove from self.nodes
        if theory_node in self.get_nodes():
            self.nodes.remove(theory_node)
            for opinion in self.get_opinions().filter(nodes__theory_node__pk=theory_node.pk):
                notify.send(
                    sender=user,
                    recipient=opinion.user,
                    verb='<# object.url {{ object }} has been removed from {{ target }}. #>',
                    description='Please update your <# target.url opinion #> to reflect the change.',
                    action_object=theory_node,
                    target=opinion,
                    level='warning',
                )
        # remove from self.flat_nodes
        self.remove_flat_node(theory_node, user=user)
        return True

    # ******************************
    # TheoryNode
    # ******************************
    def remove_flat_node(self, theory_node, user=None):
        # error checking
        if not self.assert_theory(check_nodes=True) or theory_node == self.get_intuition_node():
            return False
        if theory_node not in self.get_nodes():
            nested = False
            for subtheory_node in self.get_subtheory_nodes():
                if subtheory_node.get_nodes().filter(id=theory_node.pk).exists():
                    nested = True
                    break
            if not nested:
                self.flat_nodes.remove(theory_node)
                for parent_node in self.get_parent_nodes():
                    if theory_node not in parent_node.get_nodes():
                        parent_node.remove_flat_node(theory_node, user=user)
                return True
        return False

    # ******************************
    # TheoryNode
    # ******************************
    @classmethod
    def get_intuition_node(cls, create=True):
        """Creates and returns an intuition node."""
        # assume intuition_pk is known
        try:
            intuition_node = cls.objects.get(pk=cls.INTUITION_PK)
            if intuition_node.title01 != 'Intuition.':
                intuition_node = None
        except:
            intuition_node = None
        # get or create
        if create and intuition_node is None:
            intuition_node, created = cls.objects.get_or_create(
                node_type=cls.TYPE.EVIDENCE,
                title01='Intuition.',
            )
            cls.INTUITION_PK = intuition_node.pk
        # blah
        return intuition_node

    # ******************************
    # TheoryNode
    # ******************************
    def get_nodes(self, deleted=False, cache=False):
        """Returns a query set of the theory's nodes (use cache if available)."""
        # error checking
        if not self.assert_theory():
            return None
        # get non-deleted nodes
        if hasattr(self, 'saved_nodes'):
            nodes = self.saved_nodes
        elif cache:
            self.saved_nodes = self.nodes.filter(node_type__gt=0)
            list(self.saved_nodes)
            nodes = self.saved_nodes
        else:
            nodes = self.nodes.filter(node_type__gt=0)
        # get deleted nodes
        if deleted:
            nodes |= self.nodes.filter(node_type__lt=0)
        return nodes

    # ******************************
    # TheoryNode
    # ******************************
    def get_flat_nodes(self, deleted=False, cache=False, distinct=True):
        """Returns a query set of the theory's flat nodes/nested evidence (use cache if available)."""
        # error checking
        if not self.assert_theory():
            return None
        # non-deleted nodes
        if hasattr(self, 'saved_flat_nodes'):
            flat_nodes = self.saved_flat_nodes
        elif cache:
            self.saved_flat_nodes = self.flat_nodes.filter(
                Q(node_type=self.TYPE.FACT) |
                Q(node_type=self.TYPE.EVIDENCE)
            )
            list(self.saved_flat_nodes)
            flat_nodes = self.saved_flat_nodes
        else:
            flat_nodes = self.flat_nodes.filter(
                Q(node_type=self.TYPE.FACT) |
                Q(node_type=self.TYPE.EVIDENCE)
            )
        # get deleted nodes
        if deleted:
            # recursively build up nodes
            flat_nodes |= self.nodes.filter(
                Q(node_type=-self.TYPE.FACT) |
                Q(node_type=-self.TYPE.EVIDENCE)
            )
            for theory_node in self.nodes.filter(node_type=-self.TYPE.THEORY):
                flat_nodes |= theory_node.get_flat_nodes(
                    deleted=True, distinct=False)
            if distinct:
                flat_nodes = flat_nodes.distinct()
        return flat_nodes

    # ******************************
    # TheoryNode
    # ******************************
    def get_nested_nodes(self, deleted=False, distinct=True):
        """Returns a query set of the theory's flat nodes/nested evidence (use cache if available)."""
        # error checking
        if not self.assert_theory():
            return None
        # blah
        nodes = self.flat_nodes.filter(node_type__gt=0)
        if deleted:
            nodes |= self.nodes.filter(node_type__lt=0)
            for theory_node in self.nodes.filter(node_type=-self.TYPE.THEORY):
                nodes |= theory_node.get_nested_nodes(
                    deleted=True, distinct=False)
            if distinct:
                nodes = nodes.distinct()
        return nodes

    # ******************************
    # TheoryNode
    # ******************************
    def get_nested_subtheory_nodes(self, deleted=False, distinct=True):
        """Returns a query set of the theory's flat nodes/nested evidence (use cache if available)."""
        # error checking
        if not self.assert_theory():
            return None
        # blah
        nodes = self.flat_nodes.filter(node_type=self.TYPE.THEORY)
        if deleted:
            nodes |= self.nodes.filter(node_type=-self.TYPE.THEORY)
            for theory_node in self.nodes.filter(node_type=-self.TYPE.THEORY):
                nodes |= theory_node.get_nested_subtheory_nodes(
                    deleted=True, distinct=False)
            if distinct:
                nodes = nodes.distinct()
        return nodes

    # ******************************
    # TheoryNode
    # ******************************
    def get_evidence_nodes(self, deleted=False, cache=False):
        """Returns a query set of the theory's evidence."""
        # error checking
        if not self.assert_theory():
            return None
        # blah
        nodes = self.get_nodes().filter(
            Q(node_type=self.TYPE.FACT) |
            Q(node_type=self.TYPE.EVIDENCE)
        )
        if deleted:
            nodes |= self.nodes.filter(
                Q(node_type=-self.TYPE.FACT) |
                Q(node_type=-self.TYPE.EVIDENCE)
            )
        return nodes

    # ******************************
    # TheoryNode
    # ******************************
    def get_subtheory_nodes(self, deleted=False, cache=False):
        """Returns a query set of the theory's sub-theories."""
        # error checking
        if not self.assert_theory():
            return None
        # blah
        nodes = self.get_nodes().filter(node_type=self.TYPE.THEORY)
        if deleted:
            nodes |= self.nodes.filter(node_type=-self.TYPE.THEORY)
        return nodes

    # ******************************
    # TheoryNode
    # ******************************
    def get_parent_nodes(self, deleted=False, cache=False):
        """Returns a list of theories that are parents to this node (does not use cache)."""
        # get non-deleted nodes
        if hasattr(self, 'saved_parent_nodes'):
            parent_nodes = self.saved_parent_nodes
        elif cache:
            self.saved_parent_nodes = self.parent_nodes.filter(node_type__gt=0)
            list(self.saved_parent_nodes)
            parent_nodes = self.saved_parent_nodes
        else:
            parent_nodes = self.parent_nodes.filter(node_type__gt=0)
        # get deleted nodes
        if deleted:
            parent_nodes |= self.parent_nodes.filter(node_type__lt=0)
        return parent_nodes

    # ******************************
    # TheoryNode
    # ******************************
    def climb_theory_nodes(self, qs=None):
        """Returns a query set of all ancestors of this theory."""
        cls = self.__class__
        if qs is None:
            qs = cls.objects.none()
        parent_nodes = self.get_parent_nodes()
        for parent in parent_nodes:
            if parent not in qs:
                qs |= cls.objects.filter(pk=parent.pk)
                qs = qs | parent.climb_theory_nodes(qs)
        return qs

    # ******************************
    # TheoryNode
    # ******************************
    def get_opinions(self, cache=False, exclude=None):
        """Return a list opinions pertaining to theory."""
        # error checking
        self.assert_theory()
        # queryset
        opinions = self.opinions.filter(deleted=False)
        if hasattr(self, 'saved_opinions'):
            opinions = self.saved_opinions
        elif cache:
            self.saved_opinions = opinions
            list(opinions)
        if exclude is not None:
            opinions = opinions.exclude(user=exclude)
        return opinions

    # ******************************
    # TheoryNode
    # ******************************
    def get_opinion_nodes(self, cache=False, exclude=None):
        """Return a list opinions pertaining to theory."""
        opinion_nodes = self.opinion_nodes.filter(parent__deleted=False)
        if hasattr(self, 'saved_opinion_nodes'):
            opinions = self.saved_opinion_nodes
        elif cache:
            self.saved_opinion_nodes = opinion_nodes
            list(opinion_nodes)
        if exclude is not None:
            opinion_nodes = opinion_nodes.exclude(parent__user=exclude)
        return opinion_nodes

    # ******************************
    # TheoryNode
    # ******************************
    def get_collaborators(self, exclude=None):
        """Return a list users that have edited the theory node."""
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

    # ******************************
    # TheoryNode
    # ******************************
    def get_revisions(self):
        """Return a list revisions pertaining to theory."""
        return Version.objects.get_for_object(self)

    # ******************************
    # TheoryNode
    # ******************************
    def get_stats(self, stats_type):
        """Return the stats connected to theory_node."""
        # error checking
        if not self.assert_theory():
            return None
        if hasattr(self, 'saved_stats'):
            return self.saved_stats.get(stats_type)
        else:
            return get_or_none(self.stats.all(), stats_type=stats_type)

    # ******************************
    # TheoryNode
    # ******************************
    def get_all_stats(self, cache=False):
        """Return a list of all stats connected to theory_node, create if necessary."""
        # error checking
        if not self.assert_theory():
            return None
        if hasattr(self, 'saved_stats'):
            return self.saved_stats
        elif cache:
            self.saved_stats = QuerySetDict('stats_type', self.stats.all())
            return self.saved_stats
        else:
            return self.stats.all()

    # ******************************
    # TheoryNode
    # ******************************
    def add_to_stats(self, opinion, cache=False, save=True):
        for stats in self.get_all_stats(cache=cache):
            if stats.opinion_is_member(opinion):
                stats.add_opinion(opinion, save=save)
            stats.save_changes()

    # ******************************
    # TheoryNode
    # ******************************
    def remove_from_stats(self, opinion, cache=False, save=True):
        for stats in self.get_all_stats(cache=cache):
            stats.remove_opinion(opinion, save=save)

    # ******************************
    # TheoryNode
    # ******************************
    def save_stats(self):
        for stats in self.get_all_stats():
            stats.save_changes()

    # ******************************
    # TheoryNode
    # ******************************
    def reset_stats(self, cache=False, save=True):
        for stats in self.get_all_stats(cache=cache):
            stats.reset(save=save)

    # ******************************
    # TheoryNode
    # ******************************
    def recalculate_stats(self):
        """Recalculate all stats attached to this theory."""
        # error checking
        if not self.assert_theory(check_nodes=True):
            return False
        # reset
        self.reset_stats(cache=True, save=False)
        # add
        for opinion in self.get_opinions():
            self.add_to_stats(opinion, cache=True, save=False)
        # save
        self.save_stats()
        return True

    # ******************************
    # TheoryNode
    # ******************************
    def get_utilization(self, user=None):
        if user is None:
            return self.users.exclude(user=user).count()
        else:
            return self.users.count()

    # ******************************
    # TheoryNode
    # ******************************
    def update_hits(self, request):
        hit_count = HitCount.objects.get_for_object(self)
        hit_count_response = HitCountMixin.hit_count(request, hit_count)
        if hit_count_response.hit_counted:
            hit_count.refresh_from_db()
            self.rank = 100 * self.get_opinions().count() + 10 * \
                self.opinion_nodes.count() + hit_count.hits
            self.save()

    # ******************************
    # TheoryNode
    # ******************************
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
        log = {'sender':user, 'verb':verb, 'action_object':action_object, 'target':self}
        if stream_if_unique(self.target_actions, log):
            # parent node
            for parent_node in self.get_parent_nodes():
                if parent_node.pk not in path:
                    parent_node.update_activity_logs(
                        user, nested_verb, action_object=self, path=path)

            # categories
            for category in self.categories.all():
                category.update_activity_logs(
                    user, nested_verb, action_object=self)

            # subscribers
            log['verb'] = '<# target.a_url New activity in "{{ target }}" #>.'
            for follower in followers(self):
                if follower != user:
                    log['recipient'] = follower
                    notify_if_unique(follower, log)

    # ******************************
    # TheoryNode
    # ******************************
    def get_violations(self, opened=True, closed=True, recent=True, expired=True):

        # setup
        assert recent or expired
        assert opened or closed
        violations = Violation.objects.none()

        # filter by status
        if opened:
            violations |= self.violations.filter(
                Q(status__lt=110) &
                Q(status__gt=-110)
            )
        if closed:
            violations |= self.violations.filter(
                Q(status__gte=110) |
                Q(status__lte=-110)
            )

        # filter by date
        if recent and expired:
            pass
        elif recent:
            date00 = datetime.date.today() - datetime.timedelta(days=100)
            violations = violations.filter(pub_date__gte=date00)
        elif expired:
            date00 = datetime.date.today() - datetime.timedelta(days=100)
            violations = violations.filter(pub_date__lt=date00)

        # done
        return violations


# *******************************************************************************
# Abstract Classes
#
#
#
#
#
#
#
#
# *******************************************************************************


# ************************************************************
# TheoryPointerBase
# ************************************************************
class TheoryPointerBase():
    """Abstract manager for passing through methods to linked theory."""

    # ******************************
    # TheoryPointerBase
    # ******************************
    @classmethod
    def create(cls, theory=None, true_points=0.0, false_points=0.0):
        """Generator for constructing instances (theory attribute cannot be passed to create in abstract class)."""
        node = cls()
        node.theory = theory
        node.saved_true_points = true_points
        node.saved_false_points = false_points
        return node

    # ******************************
    # TheoryPointerBase
    # ******************************
    def check_data(self):
        if self.theory.is_evidence():
            curframe = inspect.currentframe()
            calframe = inspect.getouterframes(curframe, 2)
            logger.error(
                '1006: TheoryPointerBase is pointing at evidence (%d). Problem method: TheoryPointerBase.%s' %
                (self.theory.pk, calframe[1][3])
            )

    # ******************************
    # TheoryPointerBase
    # ******************************
    def __str__(self):
        """Pass-through for theory."""
        return self.theory.__str__()

    # ******************************
    # TheoryPointerBase
    # ******************************
    def url(self):
        """Return none. Abstract objects have no data in the db."""
        return None

    # ******************************
    # TheoryPointerBase
    # ******************************
    def compare_url(self, opinion02=None):
        """Return none. Abstract objects have no data in the db."""
        logger.error(
            '1035: There is no url for an abstract object (%s).' % str(self))
        return None

    # ******************************
    # TheoryPointerBase
    # ******************************
    def get_node_id(self):
        """Returns theory.pk."""
        return self.theory.pk

    # ******************************
    # TheoryPointerBase
    # ******************************
    def get_nodes(self):
        """Return a set of saved nodes."""
        # error checking
        self.check_data()
        # saved nodes
        if hasattr(self, 'saved_nodes'):
            return self.saved_nodes
        else:
            return []

    # ******************************
    # TheoryPointerBase
    # ******************************
    def get_flat_nodes(self):
        """Return a set of saved nodes."""
        # error checking
        self.check_data()
        # saved flat nodes
        if hasattr(self, 'saved_flat_nodes'):
            return self.saved_flat_nodes
        else:
            return []

    # ******************************
    # ToDo: Depreciate?
    # ******************************
    def get_opinions(self):
        """Return a set of saved opinions or pass-through to theory."""
        # error checking
        self.check_data()
        # saved opinions
        if hasattr(self, 'saved_opinions'):
            return self.saved_opinions
        else:
            return self.theory.get_opinions()

    # ******************************
    # TheoryPointerBase
    # ******************************
    def get_point_distribution(self):
        """Calculate true/false and facts/other point distribution (use cache if available)."""
        # error checking
        self.check_data()
        # point distribution
        if hasattr(self, 'point_distribution'):
            return self.point_distribution
        else:
            total_points = 0.0
            distribution = {'true_facts': 0.0, 'true_other': 0.0,
                            'false_facts': 0.0, 'false_other': 0.0}
            for evidence_node in self.get_flat_nodes():
                if evidence_node.is_verifiable():
                    distribution['true_facts'] += evidence_node.true_points()
                    distribution['false_facts'] += evidence_node.false_points()
                else:
                    distribution['true_other'] += evidence_node.true_points()
                    distribution['false_other'] += evidence_node.false_points()
                total_points += evidence_node.total_points()
            if total_points > 0:
                distribution['true_facts'] = distribution['true_facts'] / total_points
                distribution['true_other'] = distribution['true_other'] / total_points
                distribution['false_facts'] = distribution['false_facts'] / total_points
                distribution['false_other'] = distribution['false_other'] / total_points
            self.point_distribution = distribution
            return distribution

    # ******************************
    # TheoryPointerBase
    # ******************************
    def true_points(self):
        """Returns true points."""
        return self.saved_true_points

    # ******************************
    # TheoryPointerBase
    # ******************************
    def false_points(self):
        """Returns false points."""
        return self.saved_false_points

    # ******************************
    # TheoryPointerBase
    # ******************************
    def is_true(self):
        """Returns true if more points are awarded to true."""
        self.check_data()
        return self.true_points() >= self.false_points()

    # ******************************
    # TheoryPointerBase
    # ******************************
    def is_false(self):
        """Returns true if more points are awarded to false."""
        self.check_data()
        return self.false_points() > self.true_points()

    # ******************************
    # TheoryPointerBase
    # ******************************
    def get_point_range(self):
        """Return the range of true points this object possesses."""
        self.check_data()
        return self.true_points(), self.true_points()


# ************************************************************
# NodePointerBase
# ************************************************************
class NodePointerBase():
    """Abstract manager for passing through methods to linked theory_nodes."""

    # ******************************
    # NodePointerBase
    # ******************************
    @classmethod
    def create(cls, parent=None, theory_node=None, true_points=0.0, false_points=0.0):
        """Generator for constructing instances (theory attributes cannot be passed to create in abstract class)."""
        node = cls()
        node.parent = parent
        node.theory_node = theory_node
        node.saved_true_points = true_points
        node.saved_false_points = false_points
        return node

    # ******************************
    # NodePointerBase
    # ******************************
    def __str__(self):
        """Pass-through for theory_node."""
        return self.theory_node.__str__()

    # ******************************
    # NodePointerBase
    # ******************************
    def get_true_statement(self):
        """Pass-through method."""
        return self.theory_node.get_true_statement()

    # ******************************
    # NodePointerBase
    # ******************************
    def get_false_statement(self):
        """Pass-through method."""
        return self.theory_node.get_false_statement()

    # ******************************
    # NodePointerBase
    # ******************************
    def get_node_id(self):
        """Returns theory_node.pk."""
        return self.theory_node.pk

    # ******************************
    # NodePointerBase
    # ******************************
    def tag_id(self):
        """Pass-through for theory_node."""
        return self.theory_node.tag_id()

    # ******************************
    # NodePointerBase
    # ******************************
    def about(self):
        """Pass-through for theory_node."""
        return self.theory_node.about()

    # ******************************
    # NodePointerBase
    # ******************************
    def url(self):
        """Return a url pointing to theory_node's root (not node)."""
        return None

    # ******************************
    # NodePointerBase
    # ******************************
    def is_theory(self):
        """Pass-through for theory_node."""
        return self.theory_node.is_theory()

    # ******************************
    # NodePointerBase
    # ******************************
    def is_subtheory(self):
        """Pass-through for theory_node."""
        return self.theory_node.is_theory()

    # ******************************
    # NodePointerBase
    # ******************************
    def is_evidence(self):
        """Pass-through for theory_node."""
        return self.theory_node.is_evidence()

    # ******************************
    # NodePointerBase
    # ******************************
    def is_fact(self):
        """Pass-through for theory_node."""
        return self.theory_node.is_fact()

    # ******************************
    # NodePointerBase
    # ******************************
    def is_verifiable(self):
        """Pass-through for theory_node."""
        return self.theory_node.is_verifiable()

    # ******************************
    # NodePointerBase
    # ******************************
    def true_points(self):
        """Returns true points."""
        return self.saved_true_points

    # ******************************
    # NodePointerBase
    # ******************************
    def false_points(self):
        """Returns false points."""
        return self.saved_false_points

    # ******************************
    # NodePointerBase
    # ******************************
    def total_points(self):
        """Returns total points."""
        return self.true_points() + self.false_points()

    # ******************************
    # NodePointerBase
    # ******************************
    def true_percent(self):
        """Calculate the percentage awarded to true for this node with respect all the parent's nodes."""
        if self.parent.true_points() > 0:
            return self.true_points() / self.parent.true_points()
        else:
            return 0.0

    # ******************************
    # NodePointerBase
    # ******************************
    def false_percent(self):
        """Calculate the percentage awarded to false for this node with respect all the parent's nodes (flip true/false if necessary)."""
        if self.parent.false_points() > 0:
            return self.false_points() / self.parent.false_points()
        else:
            return 0.0

    # ******************************
    # NodePointerBase
    # ******************************
    def true_ratio(self):
        """Calculate the ratio of true points with respect to the total points."""
        if self.total_points() > 0:
            return self.true_points() / self.total_points()
        else:
            return 0.0

    # ******************************
    # NodePointerBase
    # ******************************
    def false_ratio(self):
        """Calculate the ratio of false points with respect to the total points."""
        if self.total_points() > 0:
            return self.false_points() / self.total_points()
        else:
            return 0.0


# *******************************************************************************
# Opinion Classes
#
#
#
#
#
#
#
#
# *******************************************************************************


# ************************************************************
# Opinion
# ToDo: remove all auto_now and auto_now_add
# ************************************************************
class Opinion(TheoryPointerBase, models.Model):
    """A container for user opinion data."""

    user = models.ForeignKey(
        User, related_name='opinions', on_delete=models.CASCADE)
    theory = models.ForeignKey(
        TheoryNode, related_name='opinions', on_delete=models.CASCADE)
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

    # ******************************
    # Opinion
    # ******************************
    class Meta:
        ordering = ['-rank']
        db_table = 'theories_opinion'
        verbose_name = 'Opinion'
        verbose_name_plural = 'Opinions'
        unique_together = (('theory', 'user'),)

    # ******************************
    # Opinion
    # ******************************
    @classmethod
    def get_demo(cls, theory=None):
        """Generate a demo (fake) opinion."""
        if theory is None:
            theory = TheoryNode.get_demo()
        true_points = random.random()
        false_points = 1.0 - true_points
        demo = TheoryPointerBase.create(
            theory=theory,
            true_points=true_points,
            false_points=false_points,
        )
        return demo

    # ******************************
    # Opinion
    # ******************************
    def __str__(self):
        """Pass-through for theory."""
        return self.theory.__str__()

    # ******************************
    # Opinion
    # ******************************
    def delete(self):
        self.true_input = 0
        self.false_input = 0
        self.true_total = 0
        self.false_total = 0
        self.force = False
        self.deleted = True
        self.save()

        for node in self.get_nodes():
            node.delete()

    # ******************************
    # Opinion
    # ******************************
    def is_anonymous(self):
        return self.anonymous or self.user.is_hidden()

    # ******************************
    # Opinion
    # ******************************
    def get_owner(self):
        """Return "Anonymous" if owner is hidden, otherwise return user."""
        if self.is_anonymous():
            return 'Anonymous'
        else:
            return self.user.__str__()

    # ******************************
    # Opinion
    # ******************************
    def get_owner_long(self):
        """Return "Anonymous" if owner is hidden, otherwise return user."""
        if self.is_anonymous():
            return 'Anonymous'
        else:
            return self.user.__str__(print_fullname=True)

    # ******************************
    # Opinion
    # ******************************
    def edit_url(self):
        """Return url for editing this opinion."""
        return reverse('theories:opinion-my-editor', kwargs={'pk': self.theory.pk})

    # ******************************
    # Opinion
    # ******************************
    def compare_url(self, opinion02=None):
        """Return a default url for the compare view of this opinion."""
        if opinion02 is None:
            url = reverse('theories:opinion-user_vs_slug',
                          kwargs={'pk01': self.pk, 'slug02': 'all'})
        elif isinstance(opinion02, Opinion):
            url = reverse('theories:opinion-user_vs_user',
                          kwargs={'pk01': self.pk, 'pk02': opinion02.pk})
        elif isinstance(opinion02, Stats):
            url = reverse('theories:opinion-user_vs_slug',
                          kwargs={'pk01': self.pk, 'slug02': opinion02.slug()})
        else:
            url = ''
        return url

    # ******************************
    # Opinion
    # ******************************
    def get_absolute_url(self):
        """Return the url that views the details of this opinion."""
        return reverse('theories:opinion-detail', kwargs={'pk': self.pk})

    # ******************************
    # Opinion
    # ******************************
    def url(self):
        """Return the url that views the details of this opinion."""
        return self.get_absolute_url()

    # ******************************
    # Opinion
    # ******************************
    def get_node(self, theory_node, create=False):
        """Return the opinion_node for the corresponding theory_node input."""

        # check saved nodes first
        opinion_node = None
        if hasattr(self, 'saved_nodes'):
            opinion_node = get_or_none(
                self.saved_nodes, theory_node=theory_node)

        # make db query
        if opinion_node is None:
            if create:
                opinion_node, created = self.nodes.get_or_create(
                    theory_node=theory_node)
            else:
                opinion_node = get_or_none(self.nodes, theory_node=theory_node)

        return opinion_node

    # ******************************
    # Opinion
    # ******************************
    def cache(self):
        """Save opinion nodes."""
        self.get_nodes(cache=True)

    # ******************************
    # Opinion
    # ******************************
    def get_nodes(self, cache=False, verbose_level=0):
        """Return opinion nodes (use cache if available)."""
        # debug
        if verbose_level > 0:
            print("get_nodes()")
        # get nodes
        if hasattr(self, 'saved_nodes'):
            nodes = self.saved_nodes
        elif cache:
            self.saved_nodes = self.nodes.all()
            list(self.saved_nodes)
            nodes = self.saved_nodes
        else:
            nodes = self.nodes.all()
        # debug
        if verbose_level > 0:
            for node in nodes:
                print("  - %s" % node)
        return nodes

    # ******************************
    # Opinion
    # ******************************
    def get_flat_node(self, theory_node, create=True):
        """Return a flat opinion node corresponding to the input theory_node.
           This action also populates saved_flat_nodes, which is a dictionary of
           non-db objects."""
        # setup
        if not hasattr(self, 'saved_flat_nodes'):
            self.get_flat_nodes()
        # blah
        node = self.saved_flat_nodes.get(theory_node.pk)
        if node is None and create:
            node = NodePointerBase.create(
                parent=self,
                theory_node=theory_node,
            )
            self.saved_flat_nodes.add(node)
        return node

    # ******************************
    # Opinion
    # ******************************
    def get_flat_nodes(self, verbose_level=0):
        """Return a list of non-db objects representing the flattened opinion.
           This action populates saved_flat_nodes."""

        # debug
        if verbose_level > 0:
            print("get_flat_nodes()")

        # populate flat nodes
        if not hasattr(self, 'saved_flat_nodes'):
            # initialize a set of flattened opinion_nodes
            self.saved_flat_nodes = QuerySetDict('theory_node.pk')

            # setup intuition_node
            intuition_node = self.get_flat_node(
                self.theory.get_intuition_node())

            # evidence
            for evidence_node in self.get_evidence_nodes():
                flat_node = self.get_flat_node(evidence_node.theory_node)
                flat_node.saved_true_points += evidence_node.true_percent() * self.true_points()
                flat_node.saved_false_points += evidence_node.false_percent() * \
                    self.false_points()

                # debug
                if verbose_level >= 10:
                    print('\n\n\n')
                    print(1690, '%s: %s' % (self, evidence_node))
                    print(1691, '  : true_points  = %0.2f' %
                          evidence_node.true_points())
                    print(1692, '  : false_points = %0.2f' %
                          evidence_node.false_points())
                    print(1694, '  : tt += %0.2f, tf += %0.2f, ft += %0.2f, ff += %0.2f' % (
                        evidence_node.true_percent() * self.true_points(),
                        evidence_node.false_percent() * self.false_points(),
                        0, 0,
                    ))

            # sub-theories
            for subtheory_node in self.get_subtheory_nodes():
                subtheory_opinion = subtheory_node.get_root()
                if subtheory_opinion is not None:
                    for evidence_node in subtheory_opinion.get_flat_nodes():

                        # debug
                        if verbose_level >= 10:
                            print('\n\n\n')
                            print(1720, '%s: %s' %
                                  (subtheory_opinion, evidence_node))
                            print(1721, '  : true_points  = %0.2f' %
                                  evidence_node.true_points())
                            print(1722, '  : false_points = %0.2f' %
                                  evidence_node.false_points())
                            print(1724, '  : tt += %0.2f, tf += %0.2f, ft += %0.2f, ff += %0.2f' % (
                                evidence_node.true_percent() * subtheory_node.tt_points(),
                                evidence_node.false_percent() * subtheory_node.tf_points(),
                                evidence_node.true_percent() * subtheory_node.tf_points(),
                                evidence_node.false_percent() * subtheory_node.ff_points(),
                            ))

                        flat_node = self.get_flat_node(
                            evidence_node.theory_node)
                        # true_points
                        flat_node.saved_true_points += evidence_node.true_percent() * \
                            subtheory_node.tt_points()
                        flat_node.saved_true_points += evidence_node.false_percent() * \
                            subtheory_node.ft_points()

                        # false points
                        flat_node.saved_false_points += evidence_node.true_percent() * \
                            subtheory_node.tf_points()
                        flat_node.saved_false_points += evidence_node.false_percent() * \
                            subtheory_node.ff_points()

                # intuition true points
                if subtheory_opinion is None or subtheory_opinion.true_points() == 0:
                    intuition_node.saved_true_points += subtheory_node.tt_points()
                    intuition_node.saved_false_points += subtheory_node.tf_points()

                    # debug
                    if verbose_level >= 10:
                        print('\n\n\n')
                        print(1740, '%s: %s' %
                              (subtheory_node, intuition_node))
                        print(1741, '  : true_points  = %0.2f' %
                              intuition_node.true_points())
                        print(1742, '  : false_points = %0.2f' %
                              intuition_node.false_points())
                        print(1744, '  : tt += %0.2f, tf += %0.2f, ft += %0.2f, ff += %0.2f' % (
                            subtheory_node.tt_points(), subtheory_node.tf_points(), 0, 0,
                        ))

                # intuition false points
                if subtheory_opinion is None or subtheory_opinion.false_points() == 0:
                    intuition_node.saved_true_points += subtheory_node.ft_points()
                    intuition_node.saved_false_points += subtheory_node.ff_points()

                    # debug
                    if verbose_level >= 10:
                        print('\n\n\n')
                        print(1760, '%s: %s' %
                              (subtheory_node, intuition_node))
                        print(1761, '  : true_points  = %0.2f' %
                              intuition_node.true_points())
                        print(1762, '  : false_points = %0.2f' %
                              intuition_node.false_points())
                        print(1764, '  : tt += %0.2f, tf += %0.2f, ft += %0.2f, ff += %0.2f' % (
                            0, 0, subtheory_node.ft_points(), subtheory_node.ff_points(),
                        ))

        # debug
        if verbose_level > 0:
            for flat_node in self.saved_flat_nodes:
                print("  - %s" % flat_node)

        return self.saved_flat_nodes

    # ******************************
    # Opinion
    # ******************************
    def get_intuition_node(self, create=True):
        """Return an opinion node for intuition (optionally, create the node).
           Additionally, this action adds an intuition node to theory.nodes."""
        theory_node = self.theory.get_intuition_node()
        if create:
            intuition_node, created = self.nodes.get_or_create(
                theory_node=theory_node)
        else:
            intuition_node = get_or_none(
                self.get_nodes(), theory_node=theory_node)
        return intuition_node

    # ******************************
    # Opinion
    # ******************************
    def get_evidence_nodes(self):
        """Returns a query set of the evidence opinion nodes."""

        return self.nodes.filter(
            ~Q(theory_node__node_type=TheoryNode.TYPE.THEORY) &
            ~Q(theory_node__node_type=-TheoryNode.TYPE.THEORY)
        )

    # ******************************
    # Opinion
    # ******************************
    def get_subtheory_nodes(self):
        """Return all opinion nodes that point to sub-theories of self.theory"""
        return self.nodes.filter(
            Q(theory_node__node_type=TheoryNode.TYPE.THEORY) |
            Q(theory_node__node_type=-TheoryNode.TYPE.THEORY)
        )

    # ******************************
    # Opinion
    # ******************************
    def get_parent_nodes(self):
        """Return a query set of opinion nodes that point to this opinion."""
        return OpinionNode.objects.filter(parent__user=self.user, theory_node=self.theory)

    # ******************************
    # Opinion
    # ******************************
    def update_points(self, verbose_level=0):
        """Use true_input and false_input for opinion and nodes to update true_points and false_points."""

        # debug
        if verbose_level > 0:
            print("update_points()")

        # count total points
        self.true_total = 0.0
        self.false_total = 0.0
        self.deleted = False
        for node in self.get_nodes():
            true_input = node.tt_input + node.ft_input
            false_input = node.tf_input + node.ff_input
            self.true_total += true_input
            self.false_total += false_input
            if true_input == 0 and false_input == 0:
                node.delete()
                # debug
                if verbose_level >= 10:
                    print("  delete: %s" % node)
            elif verbose_level >= 10:
                print("  %s: true_input = %d, false_input = %d" %
                      (node, true_input, false_input))

        # debug
        if verbose_level > 0:
            print("  total input points: true = %d, false = %d" %
                  (self.true_total, self.false_total))

        # intuition
        save_intuition = False
        intuition = self.get_intuition_node()
        if self.true_input > 0 and self.true_total == 0:
            intuition.tt_input = self.true_input
            self.true_total += self.true_input
            save_intuition = True
        if self.false_input > 0 and self.false_total == 0:
            intuition.tf_input = self.false_input
            self.false_total += self.false_input
            save_intuition = True
        if save_intuition:
            self.theory.add_node(self.theory.get_intuition_node())
            intuition.save()
        self.save()

    # ******************************
    # Opinion
    # ******************************
    def copy(self, user, recursive=False, path=None, verbose_level=0):
        """Copy opinion to user's opinion"""
        # debug
        if verbose_level > 0:
            print("opinion.copy()")

        # setup
        if path is None:
            path = []
        path.append(self.theory.pk)
        theory = self.theory

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

        # populate nodes
        for node in self.get_nodes():
            user_node, created = OpinionNode.objects.get_or_create(
                parent=user_opinion,
                theory_node=node.theory_node,
                tt_input=node.tt_input,
                tf_input=node.tf_input,
                ft_input=node.ft_input,
                ff_input=node.ff_input,
            )

        # points
        user_opinion.update_points()

        # recursive
        if recursive:
            for subtheory in self.get_subtheory_nodes():
                root_opinion = subtheory.get_root()
                if root_opinion is not None and root_opinion.get_node_id() not in path:
                    root_opinion.copy(user, recursive=True)

        # stats
        theory.add_to_stats(user_opinion, cache=True, save=False)
        theory.save_stats()

        # debug
        if verbose_level > 0:
            print("opinion.copy()")
        return user_opinion

    # ******************************
    # Opinion
    # ******************************
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

    # ******************************
    # Opinion
    # ******************************
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

    # ******************************
    # Opinion
    # ******************************
    def swap_true_false(self):
        """Swap the true and false points of the opinion (used when swapping the title of the theory)."""

        # self
        self.true_total, self.false_total = self.false_total, self.true_total
        self.true_input, self.false_input = self.false_input, self.true_input
        self.save()

        # nodes
        for node in self.get_nodes():
            node.tt_input, node.tf_input = node.tf_input, node.tt_input
            node.ft_input, node.ff_input = node.ff_input, node.ft_input
            node.save()

    # ******************************
    # Opinion
    # ******************************
    def update_hits(self, request):
        hit_count = HitCount.objects.get_for_object(self)
        hit_count_response = HitCountMixin.hit_count(request, hit_count)
        if hit_count_response.hit_counted:
            hit_count.refresh_from_db()
            self.rank = hit_count.hits
            self.save()

    # ******************************
    # Opinion
    # ToDo: activate when opinion is modified by system
    # ******************************
    def update_activity_logs(self, user, verb='Modified', action_object=None):
        """Update activity log."""
        # setup
        system_user = User.get_system_user()

        # this activity log
        log = {'sender':system_user, 'verb':verb, 'action_object':action_object, 'target':self} # TODO: might be a bug but the prev diff had action_object = self
        stream_if_unique(self.target_actions, log)

        # subscribed users
        log['verb'] = '<# target.url {{ target.get_owner }} has modified their opinion of "{{ target }}". #>',
        for follower in followers(self):
            if follower != user:
                log['recipient'] = follower
                notify_if_unique(follower, log)

    # ******************************
    # Opinion
    # ******************************
    def is_deleted(self):
        return self.deleted


# ************************************************************
# OpinionNode
# ************************************************************
class OpinionNode(NodePointerBase, models.Model):
    """A container for user opinion dependencies."""

    parent = models.ForeignKey(
        Opinion, related_name='nodes', on_delete=models.CASCADE)
    theory_node = models.ForeignKey(
        TheoryNode, related_name='opinion_nodes', on_delete=models.CASCADE)

    tt_input = models.SmallIntegerField(default=0)
    tf_input = models.SmallIntegerField(default=0)
    ft_input = models.SmallIntegerField(default=0)
    ff_input = models.SmallIntegerField(default=0)

    # ******************************
    # OpinionNode
    # ******************************
    class Meta:
        db_table = 'theories_opinion_node'
        verbose_name = 'Opinion Node'
        verbose_name_plural = 'Opinion Nodes'
        unique_together = (('parent', 'theory_node'),)

    # ******************************
    # OpinionNode
    # ******************************
    def get_absolute_url(self):
        """Return a url pointing to the user's opinion of theory_node (not opinion_node)."""
        opinion_root = self.get_root()
        if opinion_root is None:
            return None
        elif opinion_root.anonymous == self.parent.anonymous:
            return opinion_root.url()

    # ******************************
    # OpinionNode
    # ******************************
    def url(self):
        """Return a url pointing to the user's opinion of theory_node (not opinion_node)."""
        return self.get_absolute_url()

    # ******************************
    # OpinionNode
    # ******************************
    def get_root(self):
        """Get the user opinion pointing to theory_node."""
        if hasattr(self, 'saved_root_opinion'):
            root_opinion = self.saved_root_opinion
        else:
            if self.is_subtheory():
                root_opinion = get_or_none(
                    self.theory_node.opinions, user=self.parent.user)
                self.saved_root_opinion = root_opinion
            else:
                root_opinion = None
        return root_opinion

    # ******************************
    # OpinionNode
    # ******************************
    def tt_points(self):
        """Returns the percentage of true points (not total points) for the True-True category."""
        if self.parent.true_total > 0:
            return self.tt_input / self.parent.true_total * self.parent.true_points()
        else:
            return 0.0

    # ******************************
    # OpinionNode
    # ******************************
    def tf_points(self):
        """Returns the percentage of true points (not total points) for the True-True category."""
        if self.parent.false_total > 0:
            return self.tf_input / self.parent.false_total * self.parent.false_points()
        else:
            return 0.0

    # ******************************
    # OpinionNode
    # ******************************
    def ft_points(self):
        """Returns the percentage of true points (not total points) for the True-True category."""
        if self.parent.true_total > 0:
            return self.ft_input / self.parent.true_total * self.parent.true_points()
        else:
            return 0.0

    # ******************************
    # OpinionNode
    # ******************************
    def ff_points(self):
        """Returns the percentage of true points (not total points) for the True-True category."""
        if self.parent.false_total > 0:
            return self.ff_input / self.parent.false_total * self.parent.false_points()
        else:
            return 0.0

    # ******************************
    # OpinionNode
    # ******************************
    def true_points(self):
        return self.tt_points() + self.ft_points()

    # ******************************
    # OpinionNode
    # ******************************
    def false_points(self):
        return self.tf_points() + self.ff_points()

    # ******************************
    # OpinionNode
    # ******************************
    def is_deleted(self):
        return not self.parent.theory.get_nodes().filter(pk=self.theory_node.pk).exists()


# *******************************************************************************
# Statistics
#
#
#
#
#
#
#
#
# *******************************************************************************


# ************************************************************
# Stats
# ************************************************************
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
    theory = models.ForeignKey(
        TheoryNode, related_name='stats', on_delete=models.CASCADE)
    opinions = models.ManyToManyField(
        Opinion, related_name='stats', blank=True)
    stats_type = models.SmallIntegerField(choices=TYPE)
    total_true_points = models.FloatField(default=0.0)
    total_false_points = models.FloatField(default=0.0)

    # ******************************
    # Stats
    # ******************************
    class Meta:
        db_table = 'theories_stats'
        verbose_name = 'Stats'
        verbose_name_plural = 'Stats'
        unique_together = (('theory', 'stats_type'),)

    # ******************************
    # Stats
    # ******************************
    def __str__(self):
        """Return stats_type + title."""
        return self.get_owner() + ': ' + self.theory.__str__()

    # ******************************
    # Stats
    # ToDo: fix list(cls.TYPE)
    # ******************************
    @classmethod
    def initialize(cls, theory):
        for stats_type in [x[0] for x in list(cls.TYPE)]:
            stats, created = theory.stats.get_or_create(stats_type=stats_type)

    # ******************************
    # Stats
    # ******************************
    @classmethod
    def get_slug(cls, stats_type):
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

    # ******************************
    # Stats
    # ******************************
    def slug(self):
        """Return the slug used for urls to reference this object."""
        cls = self.__class__
        return cls.get_slug(self.stats_type)

    # ******************************
    # Stats
    # ******************************
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

    # ******************************
    # Stats
    # ******************************
    def get_owner_long(self, short=False):
        """Return a human readable possessive type of this object."""
        if self.stats_type == self.TYPE.ALL:
            return "Statistics for Everyone"
        elif self.stats_type == self.TYPE.SUPPORTERS:
            return "Statistics for Supporters'"
        elif self.stats_type == self.TYPE.MODERATES:
            return "Statistics for Moderates'"
        elif self.stats_type == self.TYPE.OPPOSERS:
            return "Statistics for Opposers'"
        else:
            assert False

    # ******************************
    # Stats
    # ******************************
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

    # ******************************
    # Stats
    # ******************************
    def get_node(self, theory_node, create=True):
        """Return the stats node for the corresponding theory_node (optionally, create the stats node)."""
        # check saved nodes first
        if hasattr(self, 'saved_nodes') and theory_node.pk in self.saved_nodes:
            return self.saved_nodes.get(theory_node.pk)
        # make db query
        elif create:
            node, created = self.nodes.get_or_create(theory_node=theory_node)
            if hasattr(self, 'saved_nodes'):
                self.saved_nodes.add(node)
            return node
        else:
            return get_or_none(self.nodes, theory_node=theory_node)

    # ******************************
    # Stats
    # ******************************
    def get_nodes(self, cache=False):
        """Return the stats node for the theory (use cache if available)."""
        if hasattr(self, 'saved_nodes'):
            return self.saved_nodes
        elif cache:
            self.saved_nodes = QuerySetDict('theory_node.pk')
            for node in self.nodes.all():
                self.saved_nodes.add(node)
            return self.saved_nodes
        else:
            return self.nodes.all()

    # ******************************
    # Stats
    # ******************************
    def get_flat_node(self, theory_node, create=True):
        """Return the flat stats node for the input theory_node (optionally, create the node)."""
        # check saved nodes first
        if hasattr(self, 'saved_flat_nodes') and theory_node.pk in self.saved_flat_nodes:
            return self.saved_flat_nodes.get(theory_node.pk)
        # make db query
        elif create:
            node, created = self.flat_nodes.get_or_create(
                theory_node=theory_node)
            if hasattr(self, 'saved_flat_nodes'):
                self.saved_flat_nodes.add(node)
            return node
        else:
            return get_or_none(self.flat_nodes, theory_node=theory_node)

    # ******************************
    # Stats
    # ******************************
    def get_flat_nodes(self, cache=False):
        """Return a query set of the flat nodes/nested evidence (use cache if available)."""
        if hasattr(self, 'saved_flat_nodes'):
            return self.saved_flat_nodes
        elif cache:
            self.saved_flat_nodes = QuerySetDict('theory_node.pk')
            for node in self.flat_nodes.all():
                self.saved_flat_nodes.add(node)
            return self.saved_flat_nodes
        else:
            return self.flat_nodes.all()

    # ******************************
    # Stats
    # ******************************
    def add_opinion(self, opinion, save=True):
        if self.opinion_is_member(opinion):

            # root
            self.total_true_points += opinion.true_points()
            self.total_false_points += opinion.false_points()
            if save:
                self.save()
            else:
                self.altered = True

            # nodes
            for opinion_node in opinion.get_nodes():
                stats_node = self.get_node(
                    theory_node=opinion_node.theory_node)
                stats_node.total_true_points += opinion_node.true_points()
                stats_node.total_false_points += opinion_node.false_points()
                if save:
                    stats_node.save()
                else:
                    stats_node.altered = True

            # flat_nodes
            for flat_opinion_node in opinion.get_flat_nodes():
                flat_stats_node = self.get_flat_node(
                    theory_node=flat_opinion_node.theory_node)
                flat_stats_node.total_true_points += flat_opinion_node.true_points()
                flat_stats_node.total_false_points += flat_opinion_node.false_points()
                if save:
                    flat_stats_node.save()
                else:
                    flat_stats_node.altered = True

            # add
            self.opinions.add(opinion)

    # ******************************
    # Stats
    # ******************************
    def remove_opinion(self, opinion, save=True):
        if self.opinions.filter(pk=opinion.pk).exists():

            # root
            self.total_true_points -= opinion.true_points()
            self.total_false_points -= opinion.false_points()
            if save:
                self.save()
            else:
                self.altered = True

            # nodes
            for opinion_node in opinion.get_nodes():
                stats_node = self.get_node(
                    theory_node=opinion_node.theory_node)
                stats_node.total_true_points -= opinion_node.true_points()
                stats_node.total_false_points -= opinion_node.false_points()
                if save:
                    stats_node.save()
                else:
                    stats_node.altered = True

            # flat_nodes
            for flat_opinion_node in opinion.get_flat_nodes():
                flat_stats_node = self.get_flat_node(
                    theory_node=opinion_node.theory_node)
                flat_stats_node.total_true_points -= flat_opinion_node.true_points()
                flat_stats_node.total_false_points -= flat_opinion_node.false_points()
                if save:
                    stats_node.save()
                else:
                    stats_node.altered = True

            # remove
            self.opinions.remove(opinion)

    # ******************************
    # Stats
    # ******************************
    def get_opinions(self):
        """Return a query set of all opinions that meet the stats category's criterion."""
        return self.opinions.filter(deleted=False)

    # ******************************
    # Stats
    # ******************************
    def url(self):
        """Return the url for viewing the details of this object (opinion-details)."""
        return reverse('theories:opinion-slug', kwargs={'pk': self.get_node_id(), 'slug': self.slug()})

    # ******************************
    # Stats
    # ******************************
    def compare_url(self, opinion02=None):
        """Return a url to compare this object with a default object (opinion-compare)."""
        cls = self.__class__
        if opinion02 is None:
            if self.stats_type == self.TYPE.MODERATES:
                url = reverse(
                    'theories:opinion-slug_vs_slug',
                    kwargs={'theory_pk': self.theory.pk, 'slug01': self.slug(
                    ), 'slug02': cls.get_slug(cls.TYPE.ALL)}
                )
            else:
                url = reverse(
                    'theories:opinion-slug_vs_slug',
                    kwargs={'theory_pk': self.theory.pk, 'slug01': self.slug(
                    ), 'slug02': cls.get_slug(cls.TYPE.MODERATES)}
                )
        elif isinstance(opinion02, Opinion):
            url = reverse(
                'theories:opinion-slug_vs_user',
                kwargs={'slug01': self.slug(), 'pk02': opinion02.pk}
            )
        elif isinstance(opinion02, Stats):
            url = reverse(
                'theories:opinion-slug_vs_slug',
                kwargs={'theory_pk': self.theory.pk,
                        'slug01': self.slug(), 'slug02': opinion02.slug()}
            )
        else:
            url = ''
        return url

    # ******************************
    # Stats
    # ******************************
    def opinion_is_member(self, opinion):
        """Test whether or not the opinion meets the criterion of the stat categorization."""
        if opinion.true_points() + opinion.false_points() == 0:
            return False
        elif self.stats_type == self.TYPE.ALL:
            return True
        elif self.stats_type == self.TYPE.SUPPORTERS and opinion.true_points() >= 0.666:
            return True
        elif self.stats_type == self.TYPE.MODERATES and opinion.true_points() < 0.666 and opinion.false_points() < 0.666:
            return True
        elif self.stats_type == self.TYPE.OPPOSERS and opinion.false_points() >= 0.666:
            return True
        else:
            return False

    # ******************************
    # Stats
    # ******************************
    def cache(self, lazy=True):
        """Save regular and flat node queries for the purpose of db efficiency."""
        if lazy:
            self.saved_nodes = QuerySetDict('theory_node.pk')
            self.saved_flat_nodes = QuerySetDict('theory_node.pk')
        else:
            self.get_nodes(cache=True)
            self.get_flat_nodes(cache=True)

    # ******************************
    # Stats
    # ******************************
    def true_points(self):
        """Returns true points (a percentage of total)."""
        if self.total_points() > 0:
            return self.total_true_points / self.total_points()
        else:
            return 0.0

    # ******************************
    # Stats
    # ******************************
    def false_points(self):
        """Returns false points (a percentage of total)."""
        if self.total_points() > 0:
            return self.total_false_points / self.total_points()
        else:
            return 0.0

    # ******************************
    # Stats
    # ******************************
    def total_points(self):
        """Returns total opinion points awarded to this theory."""
        return self.total_true_points + self.total_false_points

    # ******************************
    # Stats
    # ******************************
    def reset(self, save=True):
        """Reset this objects points as well as all node points."""
        # reset self
        self.total_true_points = 0.0
        self.total_false_points = 0.0
        # reset theory nodes
        for stats_node in self.get_nodes():
            stats_node.reset(save=save)
        # reset theory flat nodes
        for stats_flat_node in self.get_flat_nodes():
            stats_flat_node.reset(save=save)
        # opinions
        self.opinions.clear()
        if save:
            self.save()
        else:
            self.altered = True

    # ******************************
    # Stats
    # ******************************
    def save_changes(self):
        """Save changes to all nodes."""
        # self
        if hasattr(self, 'altered') and self.altered:
            self.altered = False
            self.save()

        # nodes
        if hasattr(self, 'saved_nodes'):
            for node in self.get_nodes():
                if hasattr(node, 'altered') and node.altered:
                    node.altered = False
                    node.save()

        # flat_nodes
        if hasattr(self, 'saved_flat_nodes'):
            for flat_node in self.get_flat_nodes():
                if hasattr(flat_node, 'altered') and flat_node.altered:
                    flat_node.altered = False
                    flat_node.save()

    # ******************************
    # Stats
    # ******************************
    def swap_true_false(self):
        """Swap the true and false points."""

        # self
        self.total_true_points, self.total_false_points = self.total_false_points, self.total_true_points
        self.save()

        # nodes
        for node in self.get_nodes():
            node.total_true_points, node.total_false_points = node.total_false_points, node.total_true_points
            node.save()

        # flat nodes
        for node in self.get_flat_nodes():
            node.total_true_points, node.total_false_points = node.total_false_points, node.total_true_points
            node.save()


# ************************************************************
# StatsNode
# ************************************************************
class StatsNode(NodePointerBase, models.Model):
    """A container for node based statistics"""
    parent = models.ForeignKey(
        Stats, related_name='nodes', on_delete=models.CASCADE)
    theory_node = models.ForeignKey(
        TheoryNode, related_name='stats_nodes', on_delete=models.CASCADE)
    total_true_points = models.FloatField(default=0.0)
    total_false_points = models.FloatField(default=0.0)

    # ******************************
    # StatsNode
    # ******************************
    class Meta:
        db_table = 'theories_stats_node'
        verbose_name = 'Stats Node'
        verbose_name_plural = 'Stats Node'
        unique_together = (('parent', 'theory_node'),)

    # ******************************
    # StatsNode
    # ******************************
    def url(self):
        """Return a url pointing to theory_node's root (not node)."""
        root = self.get_root()
        if root is None:
            return None
        else:
            return root.url()

    # ******************************
    # StatsNode
    # ******************************
    def get_root(self):
        """Get the root stats pointing to theory_node."""
        return get_or_none(self.theory_node.stats, stats_type=self.parent.stats_type)

    # ******************************
    # StatsNode
    # ******************************
    def true_points(self):
        """Returns true points (a percentage of total)."""
        if self.parent.total_points() > 0:
            return self.total_true_points / self.parent.total_points()
        else:
            return 0.0

    # ******************************
    # StatsNode
    # ******************************
    def false_points(self):
        """Returns false points (a percentage of total)."""
        if self.parent.total_points() > 0:
            return self.total_false_points / self.parent.total_points()
        else:
            return 0.0

    # ******************************
    # StatsNode
    # ******************************
    def total_points(self):
        """Returns total points (a percentage of total)."""
        if self.parent.total_points() > 0:
            return (self.total_true_points + self.total_false_points) / self.parent.total_points()
        else:
            return 0.0

    # ******************************
    # StatsNode
    # ******************************
    def reset(self, save=True):
        """Zero the true and false points (optionally, do not save results)."""
        self.total_true_points = 0.0
        self.total_false_points = 0.0
        if save:
            self.save()
        else:
            self.altered = True


# ************************************************************
# StatsFlatNode
# ************************************************************
class StatsFlatNode(NodePointerBase, models.Model):
    """A container for flat node (nested evidence) statistics"""
    parent = models.ForeignKey(
        Stats, related_name='flat_nodes', on_delete=models.CASCADE)
    theory_node = models.ForeignKey(
        TheoryNode, related_name='stats_flat_nodes', on_delete=models.CASCADE)
    total_true_points = models.FloatField(default=0.0)
    total_false_points = models.FloatField(default=0.0)

    # ******************************
    # StatsFlatNode
    # ******************************
    class Meta:
        db_table = 'theories_stats_flat_node'
        verbose_name = 'Stats Flat Node'
        verbose_name_plural = 'Stats Flat Nodes'
        unique_together = (('parent', 'theory_node'),)

    # ******************************
    # StatsFlatNode
    # ******************************
    def url(self):
        """Return a url pointing to theory_node's root (not node)."""
        root = self.get_root()
        if root is None:
            return None
        else:
            return root.url()

    # ******************************
    # StatsFlatNode
    # ******************************
    def get_root(self):
        """Get the root stats pointing to theory_node."""
        return get_or_none(self.theory_node.stats, stats_type=self.parent.stats_type)

    # ******************************
    # StatsFlatNode
    # ******************************
    def true_points(self):
        if self.parent.total_points() > 0:
            return self.total_true_points / self.parent.total_points()
        else:
            return 0.0

    # ******************************
    # StatsFlatNode
    # ******************************
    def false_points(self):
        if self.parent.total_points() > 0:
            return self.total_false_points / self.parent.total_points()
        else:
            return 0.0

    # ******************************
    # StatsFlatNode
    # ******************************
    def total_points(self):
        """Returns total points (a percentage of total)."""
        return self.true_points() + self.false_points()

    # ******************************
    # StatsFlatNode
    # ******************************
    def reset(self, save=True):
        """Zero the true and false points (optionally, do not save results)."""
        self.total_true_points = 0.0
        self.total_false_points = 0.0
        if save:
            self.save()
        else:
            self.altered = True
