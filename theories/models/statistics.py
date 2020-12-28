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
import logging

from django.db import models
from django.urls import reverse
from model_utils import Choices

from core.utils import get_or_none
from theories.models.content import Content
from theories.models.opinions import Opinion, OpinionBase, OpinionDependencyBase

# *******************************************************************************
# Defines
# *******************************************************************************
DEBUG = False
LOGGER = logging.getLogger('django')

# *******************************************************************************
# Models
# *******************************************************************************


class Stats(OpinionBase, models.Model):
    """A container for theory statistical data."""

    # Defines
    TYPE = Choices(
        (0, 'ALL', ('All')),
        (1, 'SUPPORTERS', ('Supporters')),
        (2, 'MODERATES', ('Moderates')),
        (3, 'OPPOSERS', ('Opposers')),
    )

    # Variables
    altered = False

    # Model Variables
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

    @classmethod
    def initialize(cls, theory):
        """[summary]

        Returns:
            [type]: [description]

        Todo:
            * Fix list(cls.TYPE).
        """
        for stats_type in [x[0] for x in list(cls.TYPE)]:
            theory.stats.get_or_create(stats_type=stats_type)

    @classmethod
    def get(cls, theory, stats_type=None, cache=False):
        """Return the stats connected to theory.

        Args:
            stats_type (Stats.TYPE or str, optional): The stats sub-type to retrive. Defaults to None.

        Returns:
            Stats or None: The stats object, or none if the query failed.
        """
        # Error checking.
        if not theory.assert_theory():
            return None
        # Setup
        if theory.stats.count() == 0:
            cls.initialize(theory)
        # Allow the method to be called with type or slug.
        if isinstance(stats_type, str):
            stats_type = Stats.slug_to_type(stats_type)
        if theory.saved_stats:
            queryset = theory.saved_stats
        elif cache:
            theory.saved_stats = theory.stats.all()
            queryset = theory.saved_stats
            list(theory.saved_stats)
        else:
            queryset = theory.stats.all()
        # Return queryset if stats_type is None
        if stats_type is None:
            return queryset
        # Return stats of requested type
        return get_or_none(queryset, stats_type=stats_type)

    @classmethod
    def add(cls, opinion, cache=False, save=True):
        theory = opinion.content
        for stats in cls.get(theory, cache=cache):
            if stats.opinion_is_member(opinion):
                stats.add_opinion(opinion, save=save)
            stats.save_changes()

    @classmethod
    def remove(cls, opinion, cache=False, save=True):
        theory = opinion.content
        for stats in cls.get(theory, cache=cache):
            stats.remove_opinion(opinion, save=save)

    @classmethod
    def get_and_save(cls, theory):
        for stats in cls.get(theory):
            stats.save_changes()

    @classmethod
    def get_and_reset(cls, theory, cache=False, save=True):
        for stats in cls.get(theory, cache=cache):
            stats.reset(save=save)

    @classmethod
    def recalculate(cls, theory):
        """Recalculate all stats attached to this theory."""
        if not theory.is_theory():
            return False
        cls.get_and_reset(theory, cache=True, save=True)
        for opinion in theory.get_opinions():
            cls.add(opinion, cache=True, save=True)
        return True

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

    def __str__(self):
        """Return stats_type + title."""
        if self.is_true():
            return self.content.true_statement()
        else:
            return self.content.false_statement()

    def reset(self, save=True):
        """Reset this objects points as well as all dependency points."""
        # Reset self
        self.total_true_points = 0.0
        self.total_false_points = 0.0
        # Reset theory dependencies
        for stats_dependency in self.get_dependencies():
            stats_dependency.reset(save=save)
            if stats_dependency.content.is_deleted():
                stats_dependency.delete()
        # Remove dependencies
        for stats_flat_dependency in self.get_flat_dependencies():
            stats_flat_dependency.reset(save=save)
            if stats_flat_dependency.content.is_deleted():
                stats_flat_dependency.delete()
        # Remove opinions
        self.opinions.clear()
        # Save
        if save:
            self.save()
        else:
            self.altered = True

    def save_changes(self):
        """Save changes to all dependencies."""
        # Update the root.
        if self.altered:
            self.altered = False
            self.save()

        # Update the dependencies.
        if self.get_saved_dependencies() is not None:
            for dependency in self.get_dependencies():
                if dependency.altered:
                    dependency.altered = False
                    dependency.save()

        # Update the flat dependencies.
        if self.get_saved_flat_dependencies() is not None:
            for flat_dependency in self.get_flat_dependencies():
                if flat_dependency.altered:
                    flat_dependency.altered = False
                    flat_dependency.save()

    def cache(self, lazy=False):
        """Save regular and flat dependency queries for the purpose of db efficiency."""
        if lazy:
            self.save_dependencies()
            self.save_flat_dependencies()
        else:
            self.save_dependencies(self.get_dependencies())
            self.save_flat_dependencies(self.get_flat_dependencies())

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
            return 'The Majority (Everyone)'
        elif self.stats_type == self.TYPE.SUPPORTERS:
            return 'The Supporters'
        elif self.stats_type == self.TYPE.MODERATES:
            return 'The Moderates'
        elif self.stats_type == self.TYPE.OPPOSERS:
            return 'The Opposers'
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
        # return super(OpinionBase, self).get_dependency(content, create)
        return super().get_dependency(content, create)

    def get_flat_dependency(self, content, create=True):
        # return super(OpinionBase, self).get_flat_dependency(content, create)
        return super().get_flat_dependency(content, create)

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

    def url(self):
        """Return the url for viewing the details of this object (opinion-analysis)."""
        return self.get_absolute_url()

    def get_absolute_url(self):
        return reverse('theories:theory-detail',
                       kwargs={
                           'content_pk': self.content.pk,
                           'opinion_slug': self.get_slug()
                       })

    def stats_url(self):
        return reverse("theories:opinion-analysis",
                       kwargs={
                           'content_pk': self.content.pk,
                           'opinion_slug': self.get_slug()
                       })

    def opinion_index_url(self):
        return reverse("theories:opinion-index",
                       kwargs={
                           'content_pk': self.content.pk,
                           'opinion_slug': self.get_slug()
                       })

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


class StatsDependencyBase(OpinionDependencyBase, models.Model):
    """A container for dependency based statistics.

    We want separate tables for dependencies and flat dependencies to help speed up the queries.

    Attributes:
        parent (Stats): The parent statistic for the dependency (the parent dependency will be a
            theory or sub-theory).
        content (Content): The dependency (theory, sub-theory, or evidence) that this stat
            pertains to.
        total_true_points (double): Total number of true points awarded to the dependency (each user
            has a total of 1.0 points to distribute to theories/dependencies).
        total_false_points (double): Total number of false points awarded to the dependency (each
            user has a total of 1.0 points to distribute to theories/dependencies).
    """
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
        abstract = True
        unique_together = (('content', 'parent'),)

    def url(self):
        """Return a url pointing to content's root (not dependency)."""
        root = self.get_root()
        if root is None:
            return self.content.url()
        else:
            return root.url()

    def get_root(self):
        """Get the root stats pointing to content."""
        if self.is_evidence():
            return None
        if self.content.stats.count() == 0:
            Stats.initialize(self.content)
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


class StatsDependency(StatsDependencyBase):
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


class StatsFlatDependency(StatsDependencyBase):
    """A container for flat dependency (nested evidence) statistics"""

    parent = models.ForeignKey(Stats, related_name='flat_dependencies', on_delete=models.CASCADE)
    content = models.ForeignKey(Content,
                                related_name='stats_flat_dependencies',
                                on_delete=models.CASCADE)

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
