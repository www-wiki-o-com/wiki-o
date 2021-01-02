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
import inspect
import logging
from enum import Enum

import reversion
from actstream.models import followers
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from hitcount.models import HitCount
from hitcount.views import HitCountMixin
from model_utils import Choices
from notifications.signals import notify
from reversion.models import Version

from core.utils import notify_if_unique, stream_if_unique
from theories.models.abstract import SavedDependencies, SavedOpinions
from users.models import User, Violation

# *******************************************************************************
# Defines
# *******************************************************************************
DEBUG = False
LOGGER = logging.getLogger('django')


class DeleteMode(Enum):
    AUTO = 1
    HARD = 2
    SOFT = 3


# *******************************************************************************
# Models
# *******************************************************************************


@reversion.register(fields=['content_type', 'title00', 'title01', 'details'])
class Content(SavedOpinions, SavedDependencies, models.Model):
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
    saved_opinion_dependencies = None

    content_type = models.SmallIntegerField(choices=TYPE)
    title00 = models.CharField(max_length=255, blank=True, null=True)
    title01 = models.CharField(max_length=255)
    details = models.TextField(max_length=10000, blank=True)

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
    saved_parents = None

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
            s = self.true_statement()
        else:
            s = self.false_statement()
        if self.is_deleted():
            s += ' (deleted)'
        return s

    def get_categories(self):
        return self.categories.all()

    def get_title(self):
        self.assert_evidence()
        return self.title01

    def true_statement(self):
        self.assert_theory()
        return self.title01

    def false_statement(self):
        self.assert_theory()
        if self.title00 is None or self.title00 == '':
            return r"{self.title01.strip('.')}, is false."
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

    def is_verifiable(self):
        """Returns true if dependency is factual evidence (verifiable)."""
        self.assert_evidence()
        return abs(self.content_type) == self.TYPE.FACT

    def is_fact(self):
        """Returns true if dependency is factual evidence (verifiable)."""
        self.assert_evidence()
        return self.is_verifiable()

    def assert_theory(self, check_dependencies=False, fix=False):
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
                log = 'Content.assert_theory: There should not be any deleted flat dependencies (pk=%d).\n' % self.pk
                log += '  %s\n' % str(self)
                for flat_dependency in self.flat_dependencies.filter(content_type__lt=0).all():
                    log += '    %s\n' % str(flat_dependency)
                LOGGER.error(log)
                if fix:
                    for flat_dependency in self.flat_dependencies.filter(content_type__lt=0):
                        self.flat_dependencies.remove(flat_dependency)
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
                LOGGER.error('592: This dependency should not have dependencies (pk=%d).', self.pk)
                return False
            if self.flat_dependencies.count() > 0:
                LOGGER.error('593: This dependency should not have flat dependencies (pk=%d).',
                             self.pk)
                return False
        return True

    def save(self, *args, user=None, **kwargs):
        """Automatically adds stats and intuition dependencies."""
        if user is not None:
            self.modified_by = user
            self.modified_date = timezone.now()
            if self.pk is None:
                self.created_by = user
        super().save(*args, **kwargs)
        if self.is_theory():
            # Stats.initialize(self)
            self.flat_dependencies.add(self.get_intuition())
        return self

    def autosave(self, user=None, force=False):
        """Saves changes and automatically archieves changes as a revision.

        Args:
            user ([type]): [description]
            force (bool, optional): [description]. Defaults to False.

        Returns:
            [type]: [description]
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

    def delete(self, user=None, mode=DeleteMode.AUTO):
        """Recursively deletes abandoned dependencies.

        Auto choice of hard and soft delete (hard=):
          - If

        Args:
            user (User, optional): The user responsible for the delete action. Defaults to None.
            mode (DeleteMode, optional): If 'hard' the content will be permently deleted, if 'soft'
              it will be flagged as deleted, if 'auto' the system will decide to use a soft or a
              hard delete. Defaults to 'auto'.

        Returns:
            [bool]: True if content was hard deleted.

        Todo:
            * Reset cache?
            * Update opinion points?

        Raises:
            ValueError: If mode is not of type DeleteMode.
        """
        # Error checking
        if self.pk == self.INTUITION_PK:
            LOGGER.error('Content::delete: Intuition dependency should not be deleted (pk=%d).',
                         self.pk)
            return False
        if self.is_deleted():
            LOGGER.error('Content::delete: Content is already deleted (pk=%d).', self.pk)
            return False
        if self.id is None:
            LOGGER.error('Content::delete: Content is already deleted or not saved.')
            return False

        # Setup
        if user is None:
            user = User.get_system_user()
        if mode == DeleteMode.AUTO:
            hard = True
            hard &= user == self.created_by
            hard &= not self.get_opinions().exists()
            hard &= not self.opinion_dependencies.exists()
        elif mode == DeleteMode.HARD:
            hard = True
        elif mode == DeleteMode.SOFT:
            hard = False
        else:
            ValueError(f'mode ({type(mode)}) is not of class DeleteMode.')

        # Recursive delete dependencies
        if self.is_theory():
            for evidence in self.get_theory_evidence():
                if evidence.get_parent_theories().count() == 1:
                    evidence.delete(user, mode)
            for subtheory in self.get_theory_subtheories():
                if not subtheory.is_root() and subtheory.get_parent_theories().count() == 1:
                    subtheory.delete(user, mode)

        # Delete content
        if hard:
            super().delete()
            return True
        else:
            # Remove flat dependencies
            self.parent_flat_theories.clear()
            for parent in self.get_parent_theories():
                if self.is_theory():
                    exclude_list = list(parent.get_dependencies().values_list(
                        'pk', flat=True)) + [self.INTUITION_PK]
                    nested_dependencies = self.get_nested_dependencies().exclude(
                        pk__in=exclude_list)
                    for theory_dependency in nested_dependencies:
                        parent.remove_flat_dependency(theory_dependency)

            # Notifications for opinions
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

            # Notifications for opinion_dependencies
            for opinion_dependency in self.opinion_dependencies.all():
                notify.send(
                    sender=user,
                    recipient=opinion_dependency.parent.user,
                    verb='<# object.url {{ object }} has been deleted. #>',
                    description='Please update your <# target opinion #> to reflect the change.',
                    action_object=self,
                    target=opinion_dependency.parent,
                    level='warning',
                )

            # Flat conent as deleted (negative => deleted)
            self.content_type = -abs(self.content_type)
            self.save(user=user)
        return False

    def cache(self, dependencies=True, flat_dependencies=True):
        """Cache sub-theory and evidence dependencies to save on db calls."""
        # error checking
        if not self.assert_theory():
            return False
        if dependencies:
            self.get_dependencies(cache=True)
        if flat_dependencies:
            self.get_flat_dependencies(cache=True)
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
        except ObjectDoesNotExist:
            intuition = None
        # get or create
        if create and intuition is None:
            intuition, _created = cls.objects.get_or_create(content_type=cls.TYPE.EVIDENCE,
                                                            title01='Intuition')
            cls.INTUITION_PK = intuition.pk
        # Blah
        return intuition

    def get_dependencies(self, deleted=False, cache=False):
        """Returns a query set of the theory's dependencies (use cache if available)."""
        # Error checking.
        if not self.assert_theory():
            return None
        # Get cached dependencies.
        dependencies = self.get_saved_dependencies()
        if dependencies is None:
            dependencies = self.dependencies.filter(content_type__gt=0)
            if cache:
                self.save_dependencies(dependencies)
        # Get deleted dependencies.
        if deleted:
            dependencies |= self.dependencies.filter(content_type__lt=0)
        return dependencies

    def get_flat_dependencies(self, deleted=False, cache=False, distinct=True):
        """Returns a query set of the theory's flat evidence.

        theory's flat dependencies/nested evidence (use cache if available).
        """
        # Error checking.
        if not self.assert_theory():
            return None
        # Check cache first.
        flat_dependencies = self.get_saved_flat_dependencies()
        if flat_dependencies is None:
            flat_dependencies = self.flat_dependencies.filter(
                Q(content_type=self.TYPE.FACT) | Q(content_type=self.TYPE.EVIDENCE))
            if cache:
                self.save_flat_dependencies(flat_dependencies)
        # Deleted dependencies.
        if deleted:
            # Recursively build up dependencies.
            flat_dependencies |= self.dependencies.filter(
                Q(content_type=-self.TYPE.FACT) | Q(content_type=-self.TYPE.EVIDENCE))
            for theory_dependency in self.dependencies.filter(content_type=-self.TYPE.THEORY):
                flat_dependencies |= theory_dependency.get_flat_dependencies(deleted=True,
                                                                             distinct=False)
        # Remove redundency.
        if distinct:
            flat_dependencies = flat_dependencies.distinct()
        return flat_dependencies

    def get_nested_dependencies(self, deleted=False, distinct=True):
        """Returns a query set of the theory's flat dependencies (evidence and subthories)."""
        # Error checking.
        if not self.assert_theory():
            return None
        # Get dependencies.
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
        # Blah
        dependencies = self.flat_dependencies.filter(content_type=self.TYPE.THEORY)
        if deleted:
            dependencies |= self.dependencies.filter(content_type=-self.TYPE.THEORY)
            for theory_dependency in self.dependencies.filter(content_type=-self.TYPE.THEORY):
                dependencies |= theory_dependency.get_nested_subtheory_dependencies(deleted=True,
                                                                                    distinct=False)
            if distinct:
                dependencies = dependencies.distinct()
        return dependencies

    def get_theory_evidence(self, deleted=False):
        """Returns a query set of the theory's evidence."""
        # error checking
        if not self.assert_theory():
            return None
        # Blah
        dependencies = self.get_dependencies().filter(
            Q(content_type=self.TYPE.FACT) | Q(content_type=self.TYPE.EVIDENCE))
        if deleted:
            dependencies |= self.dependencies.filter(
                Q(content_type=-self.TYPE.FACT) | Q(content_type=-self.TYPE.EVIDENCE))
        return dependencies

    def get_theory_subtheories(self, deleted=False):
        """Returns a query set of the theory's sub-theories."""
        # error checking
        if not self.assert_theory():
            return None
        # Blah
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
        # Error checking.
        # self.assert_theory()
        # Check cache.
        opinions = self.get_saved_opinions()
        if opinions is None:
            opinions = self.opinions.filter(deleted=False)
            if cache:
                self.save_opinions(opinions)
        if exclude is not None:
            opinions = opinions.exclude(user=exclude)
        return opinions

    def get_opinion_dependencies(self, cache=False, exclude=None):
        """Return a list opinions pertaining to theory."""
        opinion_dependencies = self.opinion_dependencies.filter(parent__deleted=False)
        if self.saved_opinion_dependencies is not None:
            opinion_dependencies = self.saved_opinion_dependencies
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

    def get_utilization(self, user=None):
        return 0  # TODO
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
