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

from actstream.models import followers
from django.db import models
from django.db.models import Count, Q
from django.template.defaultfilters import slugify
from django.urls import reverse
from hitcount.models import HitCount
from hitcount.views import HitCountMixin
from model_utils import Choices
from notifications.signals import notify

from core.utils import (QuerySetDict, get_or_none, notify_if_unique, stream_if_unique)
from theories.abstract_models import OpinionBase, OpinionDependencyBase
from theories.models.content import Content
from users.models import User

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
        """String method for OpinionDependency."""
        if self.is_true():
            return self.content.true_statement()
        else:
            return self.content.false_statement()

    def get_flat_dependency(self, content, create=True):
        # return super(OpinionBase, self).get_flat_dependency(content, create)
        print(1217, content, create)
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

    def cache(self):
        """Save opinion dependencies."""
        self.save_dependencies(self.get_dependencies())

    def get_flat_dependencies(self, cache=True, verbose_level=10):
        """Return a list of non-db objects representing the flattened opinion.
           This action populates saved_flat_dependencies.

            Todo: utilize cache argument.
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
            print(1318, type(intuition_dependency))

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
                    print(1395, intuition_dependency, intuition_dependency.true_points(),
                          intuition_dependency.false_points())

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
           Additionally, this action adds an intuition dependency to theory.dependencies."""
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

    def get_parent_opinions(self):
        """Return a query set of opinion dependencies that point to this opinion."""
        return OpinionDependency.objects.filter(parent__user=self.user, content=self.content)

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

    def copy(self, user, recursive=False, path=None, verbose_level=0):
        """Copy opinion to user's opinion"""
        # Debug
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
            Stats.remove(user_opinion, cache=True, save=False)
            user_opinion.delete()

        # new opinion
        user_opinion, _created = theory.opinions.get_or_create(user=user)
        user_opinion.true_input = self.true_input
        user_opinion.false_input = self.false_input
        user_opinion.force = self.force
        user_opinion.save()

        # populate dependencies
        for opinion_dependency in self.get_dependencies():
            OpinionDependency.objects.get_or_create(
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
                if root_opinion is not None and root_opinion.content.pk not in path:
                    root_opinion.copy(user, recursive=True)

        # stats
        Stats.add(user_opinion, cache=True, save=False)
        Stats.save(user_opinion)

        # Debug
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
        verbose_name_plural = 'Opinion Dependencies'
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
        # Error checking
        if not theory.assert_theory(check_dependencies=True):
            return False
        # Reset
        cls.get_and_reset(theory, cache=True, save=False)
        # Add
        for opinion in theory.get_opinions():
            cls.add(opinion, cache=True, save=False)
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
        # Reset self.
        self.total_true_points = 0.0
        self.total_false_points = 0.0
        # Reset theory dependencies.
        for stats_dependency in self.get_dependencies():
            stats_dependency.reset(save=save)
        # Reset theory flat dependencies.
        for stats_flat_dependency in self.get_flat_dependencies():
            stats_flat_dependency.reset(save=save)
        # Opinions
        self.opinions.clear()
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
        """Return the url for viewing the details of this object (opinion-details)."""
        return self.get_absolute_url()

    def get_absolute_url(self):
        return self.opinion_url()

    def opinion_url(self):
        return reverse('theories:opinion-detail',
                       kwargs={
                           'content_pk': self.content.pk,
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
            return None
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


def merge_content(content01, content02, user=None):
    """Merge this theory dependency with another, by absorbing the other dependency.

    Args:
        content01 ([type]): [description]
        content02 ([type]): [description]
        user ([type], optional): [description]. Defaults to None.

    Returns:
        [type]: [description]

    Todo:
        * Delete stats.
    """
    # Error checking
    if content01.content_type != content02.content_type:
        LOGGER.error('models.merge: Cannot merge content of different type (pk01=%d, pk02=%d).',
                     content01.pk, content02.pk)
        return False
    # Setup
    if user is None:
        user = User.get_system_user()
    # Theories
    if content01.is_theory():
        # Dependencies
        dependencies02 = content02.get_dependencies().exclude(pk=content01.pk)
        flat_dependencies02 = content02.get_flat_dependencies().exclude(pk=content01.pk)
        content01.dependencies.add(*dependencies02)
        content01.flat_dependencies.add(*flat_dependencies02)
    # Parents
    for parent in content02.parents.filter(~Q(pk=content01.pk)):
        parent.add_dependency(content01)
    # Opinion dependencies
    changed_theories = []
    for opinion_dependency02 in content02.opinion_dependencies.all():
        opinion = opinion_dependency02.parent
        opinion_dependency01 = get_or_none(opinion.get_dependencies(), content=content01)
        if opinion_dependency01 is None:
            Stats.remove(opinion, cache=True, save=False)
            opinion_dependency02.content = content01
            opinion_dependency02.save()
            Stats.add(opinion, cache=True, save=False)
            changed_theories.append(opinion.content)
        else:
            # notifications
            log = {}
            log['sender'] = user
            log['recipient'] = opinion.user
            log['verb'] = '<# object.url "{{ object }}" has gone through a merge that affects your opinion. #>'
            log['description'] = 'We apologize for the inconvenience. Please review your <# target.url opinion #> and adjust as necessary.'
            log['action_object'] = content01
            log['target'] = opinion
            log['level'] = 'warning'
            notify_if_unique(opinion.user, log)
    # Save changes
    for theory in changed_theories:
        theory.save_stats()
    # Delete
    content02.delete(user)
    return True


def swap_true_false(content, user=None):
    """Swap true false titles of theory and permeate the changes to opinions and stats.

    Args:
        user ([type], optional): [description]. Defaults to None.

    Returns:
        [type]: [description]

    Todo:
        * Improve stats calculation.
        * Add assert.
    """
    # Error checking
    if not content.assert_theory():
        return False
    # Setup
    if user is None:
        user = User.get_system_user()
    # Theory dependency
    content.title00, content.title01 = content.title01, content.title00
    content.save()
    # Opinions
    for opinion in content.get_opinions():
        opinion.swap_true_false()
        notify.send(
            sender=user,
            recipient=opinion.user,
            verb=
            """<# object.url The theory, "{{ object }}" has had its true and false titles swapped. #>""",
            description='This should not effect your <# target.url opinion #> in anyway.',
            action_object=content,
            target=opinion,
            level='warning',
        )
    # Stats
    for stats in Stats.get(content):
        stats.swap_true_false()
    return True


def convert_content_type(content, user=None, verifiable=False):
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
    if content.is_theory():
        # error checking
        if content.parents.count() == 0 or content.is_root():
            LOGGER.error('models.convert: Cannot convert a root theory to evidence (pk=%d).',
                         content.pk)
            return False
        # inherit dependencies
        for parent_theory in content.get_parent_theories():
            for theory_dependency in content.get_dependencies():
                parent_theory.add_dependency(theory_dependency)
        # clear stats
        for stats in Stats.get(content):
            stats.delete()
        # convert theory dependency
        if verifiable:
            content.content_type = content.TYPE.FACT
        else:
            content.content_type = content.TYPE.EVIDENCE
        content.dependencies.clear()
        content.flat_dependencies.clear()
    else:
        content.content_type = content.TYPE.THEORY
    content.save(user)
    # notifications (opinions)
    if content.is_theory():
        for opinion in content.get_opinions():
            notify.send(
                sender=user,
                recipient=opinion.user,
                verb='<# object.url The theory, "{{ object }}" has been converted to evidence. #>',
                description='This change has rendered your <# target.url opinion #> unnecessary.',
                action_object=content,
                target=opinion,
                level='warning',
            )
    # notifications (opinion_dependencies)
    for opinion_dependency in content.opinion_dependencies.all():
        print(439, opinion_dependency, opinion_dependency.parent, opinion_dependency.parent.user)
        if content.is_evidence():
            verb = '<# object.url The theory, "{{ object }}" has been converted to evidence. #>'
        else:
            verb = '<# object.url The evidence, "{{ object }}" has been converted to a sub-theory. #>'
        notify.send(
            sender=user,
            recipient=opinion_dependency.parent.user,
            verb=verb,
            description='This change affects your <# target.url opinion #> of {{ target }}.',
            action_object=content,
            target=opinion_dependency.parent,
            level='warning',
        )
    return True
