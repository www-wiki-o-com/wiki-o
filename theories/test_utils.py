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
import random

from nose.tools import nottest
from django.test import TestCase
from actstream.actions import follow

from theories.models import Category, Content
from theories.utils import get_demo_theory, get_demo_opinion
from theories.utils import create_categories, create_reserved_dependencies
from users.maintence import create_groups_and_permissions, create_test_user

# *******************************************************************************
# Defines
# *******************************************************************************

# *******************************************************************************
# Helper Methods
# *******************************************************************************


def get_or_create_theory(true_title, false_title=None, created_by=None, category='all'):
    """Generator to translate true_title input and etc to class variables."""
    kwargs = {'content_type': Content.TYPE.THEORY, 'title01': true_title}
    if false_title is not None:
        kwargs['title00'] = false_title
    if created_by is not None:
        kwargs['created_by'] = created_by
        kwargs['modified_by'] = created_by
    theory, _created = Content.objects.get_or_create(**kwargs)
    theory.categories.add(Category.get(category))
    return theory


def get_or_create_subtheory(parent_theory, true_title, false_title=None, created_by=None):
    """Generator to translate true_title input and etc to class variables."""
    # Prerequisites
    if not parent_theory.assert_theory():
        return None
    # Get or create.
    kwargs = {'content_type': Content.TYPE.THEORY, 'title01': true_title}
    if false_title is not None:
        kwargs['title00'] = false_title
    if created_by is not None:
        kwargs['created_by'] = created_by
        kwargs['modified_by'] = created_by
    subtheory, _created = Content.objects.get_or_create(**kwargs)
    parent_theory.add_dependency(subtheory)
    return subtheory


def get_or_create_evidence(parent_theory, title, created_by=None, fact=False):
    """Generator to translate title input and etc to class variables."""
    # Prerequisites
    if not parent_theory.assert_theory():
        return None
    # Get or create.
    kwargs = {'content_type': Content.TYPE.EVIDENCE, 'title01': title}
    if fact:
        kwargs['content_type'] = parent_theory.TYPE.FACT
    if created_by is not None:
        kwargs['created_by'] = created_by
        kwargs['modified_by'] = created_by
    evidence, _created = Content.objects.get_or_create(**kwargs)
    parent_theory.add_dependency(evidence)
    return evidence


@nottest
def create_test_theory(title='Theory', created_by=None, backup=False):
    """
    Create a test theory using the input data.

    @details    Primarily used for unit tests.
    @param[in]  title (optional, default 'Theory'): The theory's title.
    @param[in]  created_by (optional, default None): The user that created the theory.
    @param[in]  backup (optional, default False): If True, a backup is also created.
    """
    theory = get_or_create_theory(true_title=title, created_by=created_by)
    if backup:
        theory.save_snapshot(user=created_by)
    return theory


@nottest
def create_test_subtheory(parent_theory, title='Sub-Theory', created_by=None, backup=False):
    """
    Create a test sub-theory using the input data.

    @details    Primarily used for unit tests.
    @param[in]  parent_theory: The Content that is to be this theory's parent.
    @param[in]  title (optional, default 'Sub-Theory'): The sub-theory's title.
    @param[in]  created_by (optional, default None): The user that created the theory.
    @param[in]  backup (optional, default False): If True, a backup is also created.
    """
    subtheory = get_or_create_subtheory(
        parent_theory,
        true_title=title,
        created_by=created_by,
    )
    if backup:
        subtheory.save_snapshot(user=created_by)
    return subtheory


@nottest
def create_test_evidence(parent_theory,
                         title='Evidence',
                         fact=False,
                         created_by=None,
                         backup=False):
    """
    Create a test evidence using the input data.

    @details    Primarily used for unit tests.
    @param[in]  parent_theory: The Content that is to be this theory's parent.
    @param[in]  title (optional, default 'Evidence'): The evidence's title.
    @param[in]  created_by (optional, default None): The user that created the theory.
    @param[in]  backup (optional, default False): If True, a backup is also created.
    """
    evidence = get_or_create_evidence(
        parent_theory,
        title=title,
        fact=fact,
        created_by=created_by,
    )
    if backup:
        evidence.save_snapshot(user=created_by)
    return evidence


@nottest
def create_test_opinion(content,
                        user,
                        true_input=None,
                        false_input=None,
                        force=False,
                        dependencies=False):
    """
    Create an opinion using the input data.

    @details    Primarily used for unit tests.
    @param[in]  theory: The Content that this opinion is based on.
    @param[in]  true_input (optional, default None): The true points that are to be assigned to this opinion.
    @param[in]  false_input (optional, default None): The false points that are to be assigned to this opinion.
    @param[in]  force (optional, default False): If True, the true and false ratios will be preserved, otherwise they will be determined by the opinion's dependencies.
    @param[in]  dependencies (optional, default False): If True, a random set of dependencies will be added to the opinion.
    """
    opinion = content.opinions.create(user=user,)
    if true_input is not None:
        opinion.true_input = true_input
    if false_input is not None:
        opinion.false_input = false_input
    if force:
        opinion.force = force
    opinion.save()
    if dependencies:
        random.seed(0)
        for child_content in content.get_dependencies():
            opinion.dependencies.create(
                content=child_content,
                tt_input=random.randint(0, 100),
                tf_input=random.randint(0, 100),
                ft_input=random.randint(0, 100),
                ff_input=random.randint(0, 100),
            )
    opinion.update_points()
    content.add_to_stats(opinion)
    return opinion


# *******************************************************************************
# Unit tests
# *******************************************************************************


class UtilsTests(TestCase):

    def setUp(self):

        # Setup
        random.seed(0)
        create_groups_and_permissions()
        create_reserved_dependencies()
        create_categories()

        # Create user(s)
        self.bob = create_test_user(username='bob', password='1234')
        self.user = create_test_user(username='not bob', password='1234')

        # Create data
        self.category = Category.get('All')
        self.content = create_test_theory(created_by=self.user, backup=True)
        self.subtheory = create_test_subtheory(parent_theory=self.content, created_by=self.user)
        self.evidence = create_test_evidence(parent_theory=self.subtheory, created_by=self.user)
        self.fact = create_test_evidence(parent_theory=self.content,
                                         title='Fact',
                                         fact=True,
                                         created_by=self.user)
        self.fiction = create_test_evidence(parent_theory=self.content,
                                            title='Fiction',
                                            fact=False,
                                            created_by=self.user)
        self.intuition = Content.get_intuition()
        self.opinion = create_test_opinion(content=self.content, user=self.user, dependencies=True)
        for stats in self.content.get_all_stats():
            if stats.opinion_is_member(self.opinion):
                stats.add_opinion(self.opinion, save=False)
            stats.save_changes()
        follow(self.bob, self.content, send_action=False)

    def test_get_or_create_theory(self):
        dependency01 = get_or_create_theory(true_title='Test',
                                            false_title='Test',
                                            created_by=self.user)
        dependency02 = get_or_create_theory(true_title='Test')
        self.assertEqual(dependency01, dependency02)
        self.assertIn(dependency01, self.category.get_theories())
        self.assertTrue(dependency01.is_theory())

    def test_get_or_create_subtheory00(self):
        dependency = get_or_create_subtheory(self.evidence, true_title='TestXXX')
        self.assertIsNone(dependency)

    def test_get_or_create_subtheory01(self):
        dependency01 = get_or_create_subtheory(self.content,
                                               true_title='Test',
                                               false_title='Test',
                                               created_by=self.user)
        dependency02 = get_or_create_subtheory(self.content, true_title='Test')
        self.assertIn(dependency01, self.content.get_dependencies())
        self.assertEqual(dependency01, dependency02)
        self.assertNotIn(dependency01, self.category.get_theories())
        self.assertTrue(dependency01.is_theory())

    def test_get_or_create_evidence00(self):
        dependency = get_or_create_evidence(self.evidence, title='TestXXX')
        self.assertIsNone(dependency)

    def test_get_or_create_evidence01(self):
        dependency01 = get_or_create_evidence(self.content, title='Test', created_by=self.user)
        dependency02 = get_or_create_evidence(self.content, title='Test')
        self.assertIn(dependency01, self.content.get_dependencies())
        self.assertEqual(dependency01, dependency02)
        self.assertNotIn(dependency01, self.category.get_theories())
        self.assertTrue(dependency01.is_evidence())

    def test_get_demo_theory(self):
        demo = get_demo_theory()
        self.assertIsNotNone(demo)

    def test_get_demo(self):
        demo = get_demo_opinion()
        self.assertIsNotNone(demo)
