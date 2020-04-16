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
from django.db.models import Q
from django.urls import reverse
from hitcount.models import HitCount
from hitcount.views import HitCountMixin

from core.utils import (QuerySetDict, get_or_none, notify_if_unique, stream_if_unique)
from theories.abstract_models import OpinionBase
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
