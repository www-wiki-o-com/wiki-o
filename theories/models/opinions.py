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

from actstream.models import followers
from django.db import models
from django.db.models import Q
from django.urls import reverse
from hitcount.models import HitCount
from hitcount.views import HitCountMixin

from core.utils import QuerySetDict, get_or_none, notify_if_unique, stream_if_unique
from theories.models.content import Content
from theories.models.abstract import ContentPointer, SavedDependencies, SavedPoints
from users.models import User

# *******************************************************************************
# Defines
# *******************************************************************************
DEBUG = False
LOGGER = logging.getLogger('django')

# *******************************************************************************
# Models
# *******************************************************************************


class OpinionBase(ContentPointer, SavedDependencies, SavedPoints):
    """Abstract manager for accessing and agregating the theory's points.

    Usage: This class can also be used to construct dummy Contents that will not show up in
        the database.

    Inherited Attributes:
        content (Content): The content.
        saved_true_points (float): Cache for the true points.
        saved_false_points (float): Cache for the fasle points.
        saved_opinions (QuerySet:Opinion): Cache for the theory's opinions.
        saved_dependencies (QuerySet:Content): Cache for the the theory's dependencies.
        saved_flat_dependencies (QuerySet:Content): Cache for the theory's flat dependencies.
        saved_point_distribution (list[float]): Cache for the theory's point distribution.
    """
    dependencies = None
    flat_dependencies = None
    saved_point_distribution = None

    @classmethod
    def create(cls,
               content=None,
               true_points=0.0,
               false_points=0.0,
               dependencies=None,
               flat_dependencies=None):
        """Generator for constructing instances."""
        new_object = cls()
        new_object.content = content
        new_object.save_points(true_points, false_points)
        new_object.save_dependencies(dependencies)
        new_object.save_flat_dependencies(flat_dependencies)
        return new_object

    def check_for_errors(self):
        """A helper method for logging errors with the data."""
        if self.content.is_evidence():
            curframe = inspect.currentframe()
            calframe = inspect.getouterframes(curframe, 2)
            LOGGER.error(
                'OpinionBase.check_for_errors: is pointing at evidence (%d). '
                'Problem method: OpinionBase.%s', self.content.pk, calframe[1][3])

    def url(self):
        """Return none. Abstract objects have no data in the db."""
        return None

    def get_dependency(self, content, create=False):
        """Return the stats dependency for the corresponding content (optionally, create the stats dependency)."""
        # Get dependencies.
        dependencies = self.get_dependencies()
        # Get dependency.
        dependency = get_or_none(dependencies, content=content)
        if dependency is None and create:
            if self.dependencies is None:
                dependency = OpinionDependencyBase.create(
                    parent=self,
                    content=content,
                )
            else:
                dependency, _created = self.dependencies.get_or_create(content=content)
            # Add to cache (if it exists).
            saved_dependencies = self.get_saved_dependencies()
            if saved_dependencies is not None:
                if isinstance(saved_dependencies, QuerySetDict):
                    saved_dependencies.add(dependency)
                else:
                    self.save_dependencies(self.dependencies.all())
        return dependency

    def get_dependencies(self, cache=False):
        """Return the stats dependency for the theory (use cache if available)."""
        # Check cache first.
        dependencies = self.get_saved_dependencies()
        if dependencies is None and self.dependencies is not None:
            if self.dependencies is not None:
                dependencies = self.dependencies.all()
            if cache:
                self.save_dependencies(dependencies)
        return dependencies

    def get_flat_dependency(self, content, create=False):
        """Return the flat stats dependency for the input content (optionally, create the dependency)."""
        # Get dependencies.
        flat_dependencies = self.get_flat_dependencies()
        # Get dependency.
        dependency = get_or_none(flat_dependencies, content=content)
        if dependency is None and create:
            if self.flat_dependencies is None:
                dependency = OpinionDependencyBase.create(
                    parent=self,
                    content=content,
                )
            else:
                dependency, _created = self.flat_dependencies.get_or_create(content=content)
            # Add to cache (if it exists).
            saved_flat_dependencies = self.get_saved_flat_dependencies()
            if saved_flat_dependencies is not None:
                if isinstance(saved_flat_dependencies, QuerySetDict):
                    saved_flat_dependencies.add(dependency)
                else:
                    self.save_flat_dependencies(self.flat_dependencies.all())
        return dependency

    def get_flat_dependencies(self, cache=False, verbose_level=0):
        """Return a query set of the flat dependencies/nested evidence (use cache if available)."""
        # Check cache first.
        flat_dependencies = self.get_saved_flat_dependencies()
        if flat_dependencies is None and self.flat_dependencies is not None:
            flat_dependencies = self.flat_dependencies.all()
            if cache:
                self.save_flat_dependencies(flat_dependencies)
        if verbose_level >= 999:
            print('get_flat_dependencies:', flat_dependencies)
        return flat_dependencies

    def get_point_range(self):
        """Return the range of true points this object possesses."""
        self.check_for_errors()
        return self.true_points(), self.true_points()

    def get_point_distribution(self):
        """Calculate true/false and facts/other point distribution (use cache if available)."""
        self.check_for_errors()
        if self.saved_point_distribution is not None:
            return self.saved_point_distribution
        total_points = 0.0
        distribution = {
            'true_facts': 0.0,
            'true_other': 0.0,
            'false_facts': 0.0,
            'false_other': 0.0
        }
        for evidence in self.get_flat_dependencies():
            if evidence.is_verifiable():
                distribution['true_facts'] += evidence.true_points()
                distribution['false_facts'] += evidence.false_points()
            else:
                distribution['true_other'] += evidence.true_points()
                distribution['false_other'] += evidence.false_points()
            total_points += evidence.total_points()
        if total_points > 0:
            distribution['true_facts'] = distribution['true_facts'] / total_points
            distribution['true_other'] = distribution['true_other'] / total_points
            distribution['false_facts'] = distribution['false_facts'] / total_points
            distribution['false_other'] = distribution['false_other'] / total_points
        self.saved_point_distribution = distribution
        return distribution

    def is_true(self):
        """Returns true if more points are awarded to true."""
        return self.true_points() >= self.false_points()

    def is_false(self):
        """Returns true if more points are awarded to false."""
        return self.false_points() > self.true_points()


class Opinion(OpinionBase, models.Model):
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
        """String method for Opinion."""
        if self.is_true():
            return self.content.true_statement()
        else:
            return self.content.false_statement()

    def get_flat_dependency(self, content, create=True):
        # return super(OpinionBase, self).get_flat_dependency(content, create)
        return super().get_flat_dependency(content, create)

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

    def get_owner(self):
        """Return "Anonymous" if owner is hidden, otherwise return user."""
        if self.is_anonymous():
            return 'Anonymous'
        return self.user.__str__()

    def get_owner_long(self):
        """Return "Anonymous" if owner is hidden, otherwise return user."""
        if self.is_anonymous():
            return 'Anonymous'
        return self.user.__str__(print_fullname=True)

    def url(self):
        """Return the url that views the details of this opinion."""
        return self.get_absolute_url()

    def get_absolute_url(self):
        """Return the url that views the details of this opinion."""
        return reverse('theories:theory-detail',
                       kwargs={
                           'content_pk': self.content.pk,
                           'opinion_pk': self.pk
                       })

    def stats_url(self):
        """Return url for viewing the stats of this opinion."""
        return reverse('theories:opinion-analysis',
                       kwargs={
                           'content_pk': self.content.pk,
                           'opinion_pk': self.pk
                       })

    def edit_url(self):
        """Return url for editing this opinion."""
        return reverse('theories:opinion-my-editor', kwargs={'content_pk': self.content.pk})

    def cache(self):
        """Save opinion dependencies."""
        self.save_dependencies(self.get_dependencies())

    def get_flat_dependencies(self, cache=True, verbose_level=0):
        """Return a list of non-db objects representing the flattened opinion.

        This action populates saved_flat_dependencies.
        """

        # Debug
        if verbose_level > 0:
            print(self, "get_flat_dependencies()")

        # Check cache first.
        flat_dependencies = self.get_saved_flat_dependencies()

        # Populate flat dependencies.
        if flat_dependencies is None:

            # Initialize a set of flattened opinion_dependencies
            flat_dependencies = QuerySetDict('content.pk')
            self.save_flat_dependencies(flat_dependencies)

            # Get the intuition node.
            intuition_dependency = self.get_flat_dependency(self.content.get_intuition())

            # Evidence
            for evidence in self.get_theory_evidence():
                flat_dependency = self.get_flat_dependency(evidence.content)
                flat_dependency.save_points(
                    flat_dependency.true_points() + evidence.true_percent() * self.true_points(),
                    flat_dependency.false_points() + evidence.false_percent() * self.false_points())

                # Debug
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

            # Sub-theories
            for subtheory in self.get_theory_subtheories():
                subtheory_opinion = subtheory.get_root()
                if subtheory_opinion is not None:
                    for evidence in subtheory_opinion.get_flat_dependencies():
                        flat_dependency = self.get_flat_dependency(evidence.content)
                        flat_dependency.save_points(
                            flat_dependency.true_points() +
                            evidence.true_percent() * subtheory.tt_points() +
                            evidence.false_percent() * subtheory.ft_points(),
                            flat_dependency.false_points() +
                            evidence.true_percent() * subtheory.tf_points() +
                            evidence.false_percent() * subtheory.ff_points())

                        # Debug
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

                # Intuition true points.
                if subtheory_opinion is None or subtheory_opinion.true_points() == 0:
                    intuition_dependency.save_points(
                        intuition_dependency.true_points() + subtheory.tt_points(),
                        intuition_dependency.false_points() + subtheory.tf_points(),
                    )

                    # Debug
                    if verbose_level >= 10:
                        print('\n\n\n')
                        print(1740, '%s: %s' % (subtheory, intuition_dependency))
                        print(1741, '  : true_points  = %0.2f' % intuition_dependency.true_points())
                        print(1742,
                              '  : false_points = %0.2f' % intuition_dependency.false_points())
                        print(
                            1744, '  : tt += %0.2f, tf += %0.2f, ft += %0.2f, ff += %0.2f' %
                            (subtheory.tt_points(), subtheory.tf_points(), subtheory.ft_points(),
                             subtheory.ff_points()))

                # Intuition true points.
                if subtheory_opinion is None or subtheory_opinion.false_points() == 0:
                    intuition_dependency.save_points(
                        intuition_dependency.true_points() + subtheory.ft_points(),
                        intuition_dependency.false_points() + subtheory.ff_points(),
                    )

                    # Debug
                    if verbose_level >= 10:
                        print('\n\n\n')
                        print(1760, '%s: %s' % (subtheory, intuition_dependency))
                        print(1761, '  : true_points  = %0.2f' % intuition_dependency.true_points())
                        print(1762,
                              '  : false_points = %0.2f' % intuition_dependency.false_points())
                        print(
                            1764, '  : tt += %0.2f, tf += %0.2f, ft += %0.2f, ff += %0.2f' %
                            (subtheory.tt_points(), subtheory.tf_points(), subtheory.ft_points(),
                             subtheory.ff_points()))
            if cache:
                self.save_flat_dependencies(flat_dependencies)

        # Debug
        if verbose_level > 0:
            print(1407, self)
            for flat_dependency in flat_dependencies:
                print("  - %s %0.2f:%0.2f" % (flat_dependency, flat_dependency.true_points(),
                                              flat_dependency.false_points()))

        return flat_dependencies

    def get_intuition(self, create=True):
        """Return an opinion dependency for intuition (optionally, create the dependency).

        Additionally, this action adds an intuition dependency to theory.dependencies.
        """
        content = self.content.get_intuition()
        if create:
            intuition, _created = self.dependencies.get_or_create(content=content)
        else:
            intuition = get_or_none(self.get_dependencies(), content=content)
        return intuition

    def get_theory_evidence(self):
        """Returns a query set of the evidence opinion dependencies."""

        return self.get_dependencies().filter(~Q(content__content_type=Content.TYPE.THEORY) &
                                              ~Q(content__content_type=-Content.TYPE.THEORY))

    def get_theory_subtheories(self):
        """Return all opinion dependencies that point to sub-theories of self.content"""
        return self.get_dependencies().filter(
            Q(content__content_type=Content.TYPE.THEORY) |
            Q(content__content_type=-Content.TYPE.THEORY))

    def update_points(self, verbose_level=0):
        """Use true_input and false_input for opinion and dependencies to update true_points and false_points."""

        # Debug
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
                # Debug
                if verbose_level >= 10:
                    print("  delete: %s" % dependency)
            elif verbose_level >= 10:
                print("  %s: true_input = %d, false_input = %d" %
                      (dependency, true_input, false_input))

        # Debug
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

    def true_points(self):
        """Return the total true points for opinion."""
        if self.force:
            total = self.true_input + self.false_input
            if total > 0:
                return self.true_input / total
            return 0.0
        total = self.true_total + self.false_total
        if total > 0:
            return self.true_total / total
        return 0.0

    def false_points(self):
        """Return the total false points for opinion."""
        if self.force:
            total = self.true_input + self.false_input
            if total > 0:
                return self.false_input / total
            return 0.0
        total = self.true_total + self.false_total
        if total > 0:
            return self.false_total / total
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
        log['verb'] = '<# target.url {{ target.get_owner }} has modified their opinion of "{{ target }}". #>'
        for follower in followers(self):
            if follower != user:
                log['recipient'] = follower
                notify_if_unique(follower, log)

    def is_deleted(self):
        return self.deleted

    def get_parent_opinions(self):
        """Return a query set of opinion dependencies that point to this opinion."""
        return OpinionDependency.objects.filter(parent__user=self.user, content=self.content)


class OpinionDependencyBase(ContentPointer, SavedPoints):
    """Abstract manager for passing through methods to linked theory_dependencies.

    Todo:
        * Move to seperate file.
    """
    parent = None

    @classmethod
    def create(cls, parent=None, content=None, true_points=0.0, false_points=0.0):
        """Generator for constructing instances."""
        new_object = cls()
        new_object.parent = parent
        new_object.content = content
        new_object.save_points(true_points, false_points)
        return new_object

    def total_points(self):
        """Returns total points."""
        return self.true_points() + self.false_points()

    def true_percent(self):
        """Calculate the percentage awarded to true with respect all parent dependencies.

        The true and true points are flipped when necessary.
        """
        if self.parent.true_points() > 0:
            return self.true_points() / self.parent.true_points()
        return 0.0

    def false_percent(self):
        """Calculate the percentage awarded to false with respect all parent dependencies.

        The true and false points are flipped when necessary.
        """
        if self.parent.false_points() > 0:
            return self.false_points() / self.parent.false_points()
        return 0.0

    def true_ratio(self):
        """Calculate the ratio of true points with respect to the total points."""
        if self.total_points() > 0:
            return self.true_points() / self.total_points()
        return 0.0

    def false_ratio(self):
        """Calculate the ratio of false points with respect to the total points."""
        if self.total_points() > 0:
            return self.false_points() / self.total_points()
        return 0.0


class OpinionDependency(OpinionDependencyBase, models.Model):
    """A container for user opinion dependencies."""

    parent = models.ForeignKey(Opinion, related_name='dependencies', on_delete=models.CASCADE)
    content = models.ForeignKey(Content,
                                related_name='opinion_dependencies',
                                on_delete=models.CASCADE)

    tt_input = models.SmallIntegerField(default=0)
    tf_input = models.SmallIntegerField(default=0)
    ft_input = models.SmallIntegerField(default=0)
    ff_input = models.SmallIntegerField(default=0)
    rank = models.FloatField(default=0.0)

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
        ordering = ['-rank']
        db_table = 'theories_opinion_dependency'
        verbose_name = 'Opinion Dependency'
        verbose_name_plural = 'Opinion Dependencies'
        unique_together = (('content', 'parent'),)

    def save(self, *args, **kwargs):
        """Saves and updates rank."""
        self.rank = self.total_points()
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return a url pointing to the user's opinion of content (not opinion_dependency)."""
        opinion_root = self.get_root()
        if opinion_root is None:
            return None
        if opinion_root.anonymous == self.parent.anonymous:
            return opinion_root.url()
        raise RuntimeError

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
        return 0.0

    def tf_points(self):
        """Returns the percentage of true points (not total points) for the True-True category."""
        if self.parent.false_total > 0:
            return self.tf_input / self.parent.false_total * self.parent.false_points()
        return 0.0

    def ft_points(self):
        """Returns the percentage of true points (not total points) for the True-True category."""
        if self.parent.true_total > 0:
            return self.ft_input / self.parent.true_total * self.parent.true_points()
        return 0.0

    def ff_points(self):
        """Returns the percentage of true points (not total points) for the True-True category."""
        if self.parent.false_total > 0:
            return self.ff_input / self.parent.false_total * self.parent.false_points()
        return 0.0

    def true_points(self):
        return self.tt_points() + self.ft_points()

    def false_points(self):
        return self.tf_points() + self.ff_points()

    def is_deleted(self):
        return not self.parent.content.get_dependencies().filter(pk=self.content.pk).exists()
