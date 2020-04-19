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

from django.test import TestCase
from actstream.actions import follow

from theories.models.content import Content
from theories.models.categories import Category
from theories.utils import get_demo_theory, get_demo_opinion
from theories.utils import create_categories, create_reserved_dependencies
from users.maintence import create_groups_and_permissions, create_test_user

from theories.tests.utils import *

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
        for stats in Stats.get(self.content):
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
