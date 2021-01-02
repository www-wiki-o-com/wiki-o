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
import datetime
import random

from actstream.actions import follow
from django.test import TestCase
from django.urls import reverse
from hitcount.models import HitCount

from core.utils import get_or_none
from theories.model_utils import (convert_content_type, copy_opinion, get_compare_url,
                                  merge_content, swap_true_false)
from theories.models.categories import Category
from theories.models.content import Content, DeleteMode
from theories.models.statistics import Stats
from theories.tests.utils import (create_test_evidence, create_test_opinion, create_test_subtheory,
                                  create_test_theory, get_or_create_evidence,
                                  get_or_create_subtheory)
from theories.utils import create_categories, create_reserved_dependencies
from users.maintence import create_groups_and_permissions, create_test_user

# *******************************************************************************
# Defines
# *******************************************************************************


# ************************************************************
# CategoryTests
#
#
#
#
#
#
#
#
# ************************************************************
class CategoryTests(TestCase):

    def setUp(self):

        # Setup
        random.seed(0)
        create_groups_and_permissions()
        create_reserved_dependencies()
        create_categories()
        Content.update_intuition()

        # Create user(s)
        self.bob = create_test_user(username='bob', password='1234')
        self.user = create_test_user(username='not_bob', password='1234')

        # Create data
        self.content = create_test_theory(created_by=self.user)
        self.category = Category.get('All')
        follow(self.bob, self.category, send_action=False)

    def test_str(self):
        self.assertEqual(str(self.category), 'All')

    def test_save(self):
        category = Category.objects.create(title='New')
        self.assertEqual(category.slug, 'new')

    def test_get_exisiting(self):
        category = Category.get('All')
        self.assertEqual(category.slug, 'all')

    def test_get_none(self):
        category = Category.get('blah', create=False)
        self.assertIsNone(category)

    def test_get_create(self):
        category = Category.get('blah', create=True)
        self.assertIsNotNone(category)

    def test_get_all(self):
        categories = [x.slug for x in Category.get_all(exclude=['All'])]
        self.assertIn('legal', categories)
        self.assertIn('health', categories)
        self.assertIn('conspiracy', categories)
        self.assertIn('pop-culture', categories)
        self.assertIn('science', categories)
        self.assertIn('politics', categories)
        self.assertNotIn('all', categories)

    def test_get_url(self):
        self.assertEqual(self.category.get_absolute_url(), '/theories/all/')

    def test_url(self):
        self.assertEqual(self.category.url(), '/theories/all/')

    def test_activity_url(self):
        self.assertEqual(self.category.activity_url(), '/theories/all/activity/')

    def test_get_theories(self):
        self.assertIn(self.content, self.category.get_theories())

    def test_update_activity_logs(self):
        verb = "Yo Bob, what's up? Check out this theory yo."

        self.category.update_activity_logs(self.user, verb, action_object=self.content)
        self.assertEqual(self.category.target_actions.count(), 1)
        self.assertEqual(self.bob.notifications.count(), 1)

        self.category.update_activity_logs(self.user, verb, action_object=self.content)
        self.assertEqual(self.category.target_actions.count(), 1)
        self.assertEqual(self.bob.notifications.count(), 1)

        action = self.category.target_actions.first()
        action.timestamp -= datetime.timedelta(seconds=36000)
        action.save()

        notification = self.bob.notifications.first()
        notification.timestamp -= datetime.timedelta(seconds=36000)
        notification.save()

        self.category.update_activity_logs(self.user, verb, action_object=self.content)
        self.assertEqual(self.category.target_actions.count(), 2)
        self.assertEqual(self.bob.notifications.count(), 2)


# ************************************************************
# ContentTests
#
#
#
#
#
#
#
#
#
# ************************************************************
class ContentTests(TestCase):

    def setUp(self):

        # setup
        random.seed(0)
        create_groups_and_permissions()
        create_reserved_dependencies()
        create_categories()

        # create user(s)
        self.bob = create_test_user(username='bob', password='1234')
        self.user = create_test_user(username='not bob', password='1234')

        # create data
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

    def test_str(self):
        dependency01 = get_or_create_subtheory(self.content, true_title='Test01', false_title='XXX')
        dependency02 = get_or_create_evidence(self.content, title='Test02')
        self.assertEqual(dependency01.__str__(1, 0), 'Test01')
        self.assertEqual(dependency01.__str__(0, 1), 'XXX')
        self.assertEqual(str(dependency01), 'Test01')
        self.assertEqual(str(dependency02), 'Test02')

        dependency01.delete()
        self.assertEqual(str(dependency01), 'Test01 (deleted)')

    def test_true_statement(self):
        self.assertEqual(self.content.true_statement(), self.content.title01)

    def test_false_statement(self):
        self.assertEqual(self.content.false_statement(), self.content.__str__(0, 1))

    def test_get_title(self):
        self.assertEqual(self.evidence.get_title(), self.evidence.title01)

    def test_about(self):
        self.assertEqual(self.content.about().strip(), self.content.title01)

    def test_get_absolute_url(self):
        self.assertIsNotNone(self.content.get_absolute_url())

    def test_url(self):
        self.assertIsNotNone(self.content.url())

    def test_activity_url(self):
        self.assertIsNotNone(self.content.activity_url())
        self.assertIsNotNone(self.evidence.activity_url())

    def test_tag_id(self):
        self.assertIsNotNone(self.content.tag_id())

    def test_is_deleted(self):
        self.assertFalse(self.content.is_deleted())
        self.content.delete()
        self.assertTrue(self.content.is_deleted())

    def test_is_theory(self):
        self.assertTrue(self.content.is_theory())
        self.assertTrue(self.subtheory.is_theory())
        self.assertFalse(self.evidence.is_theory())

    def test_is_evidence(self):
        self.assertTrue(self.evidence.is_evidence())
        self.assertFalse(self.content.is_evidence())
        self.assertFalse(self.subtheory.is_evidence())

    def test_is_root(self):
        self.assertTrue(self.content.is_root())
        self.assertFalse(self.subtheory.is_root())
        self.assertFalse(self.evidence.is_root())

    def test_is_fact(self):
        self.assertTrue(self.fact.is_fact())
        self.assertFalse(self.evidence.is_fact())
        self.assertFalse(self.content.is_fact())
        self.assertFalse(self.subtheory.is_fact())

    def test_is_verifiable(self):
        self.assertTrue(self.fact.is_verifiable())
        self.assertFalse(self.evidence.is_verifiable())
        self.assertFalse(self.content.is_verifiable())
        self.assertFalse(self.subtheory.is_verifiable())

    def test_assert_theory(self):
        self.evidence.dependencies.add(self.content)
        self.evidence.flat_dependencies.add(self.content)
        self.assertTrue(self.content.assert_theory())
        self.assertTrue(self.subtheory.assert_theory())
        self.assertFalse(self.evidence.assert_theory())

        self.evidence.delete()
        self.subtheory.flat_dependencies.add(self.evidence)
        self.assertFalse(self.subtheory.assert_theory(check_dependencies=True))

        # ToDo: test log

    def test_assert_evidence(self):
        self.assertTrue(self.evidence.assert_evidence())
        self.assertFalse(self.content.assert_evidence())
        self.assertFalse(self.subtheory.assert_evidence())

        self.evidence.flat_dependencies.add(self.content)
        self.assertFalse(self.evidence.assert_evidence(check_dependencies=True))

        self.evidence.dependencies.add(self.content)
        self.assertFalse(self.evidence.assert_evidence(check_dependencies=True))

        # ToDo: test log

    def test_save01(self):
        self.content.title01 = 'blah'
        self.content.save()
        self.content.refresh_from_db()
        self.assertEqual(self.content.title01, 'blah')

    def test_save02(self):
        dependency01 = Content(title01='Test', content_type=Content.TYPE.THEORY)
        dependency01.save(user=self.user)
        self.assertEqual(dependency01.created_by, self.user)
        self.assertEqual(dependency01.modified_by, self.user)
        self.assertIn(Content.get_intuition(), dependency01.get_flat_dependencies())

    def test_autosave(self):
        assert self.evidence.get_revisions().count() == 0

        self.evidence.autosave(self.bob)
        self.assertEqual(self.evidence.get_revisions().count(), 1)

        self.evidence.autosave(self.bob, force=True)
        self.assertEqual(self.evidence.get_revisions().count(), 2)

    def test_save_snapshot(self):
        assert self.evidence.get_revisions().count() == 0

        self.evidence.save_snapshot(self.bob)
        self.assertEqual(self.evidence.get_revisions().count(), 1)

        self.evidence.save_snapshot(self.bob)
        self.assertEqual(self.evidence.get_revisions().count(), 1)

    def test_add_dependency(self):
        new = Content.objects.create(title01='new', content_type=Content.TYPE.EVIDENCE)

        result = self.evidence.add_dependency(new)
        self.assertFalse(result)

        result = self.subtheory.add_dependency(new)
        self.assertTrue(result)
        self.assertIn(new, self.subtheory.dependencies.all())
        self.assertIn(new, self.subtheory.flat_dependencies.all())
        self.assertIn(new, self.content.flat_dependencies.all())

    def test_add_dependencies(self):
        new = Content.objects.create(title01='new', content_type=Content.TYPE.EVIDENCE)
        result = self.evidence.add_dependencies([new])
        self.assertFalse(result)

    def test_get_dependencies00(self):
        dependencies = self.evidence.get_dependencies()
        self.assertIsNone(dependencies)

    def test_get_dependencies01(self):

        self.subtheory.delete()

        dependencies = self.content.get_dependencies()
        self.assertIn(self.fact, dependencies)
        self.assertIn(self.fiction, dependencies)
        self.assertNotIn(self.subtheory, dependencies)
        self.assertEqual(dependencies.count(), 2)
        self.assertIsNone(self.content.get_saved_dependencies())

        dependencies = self.content.get_dependencies(deleted=True)
        self.assertIn(self.fact, dependencies)
        self.assertIn(self.fiction, dependencies)
        self.assertIn(self.subtheory, dependencies)
        self.assertEqual(dependencies.count(), 3)
        self.assertIsNone(self.content.get_saved_dependencies())

    def test_get_dependencies02(self):

        dependencies = self.content.get_dependencies(cache=True)
        self.assertIn(self.fact, dependencies)
        self.assertIn(self.fiction, dependencies)
        self.assertIn(self.subtheory, dependencies)
        self.assertEqual(dependencies.count(), 3)
        self.assertEqual(self.content.get_saved_dependencies(), dependencies)

        dependencies = self.content.get_dependencies(cache=True)
        self.assertIn(self.fact, dependencies)
        self.assertIn(self.fiction, dependencies)
        self.assertIn(self.subtheory, dependencies)
        self.assertEqual(dependencies.count(), 3)
        self.assertEqual(self.content.get_saved_dependencies(), dependencies)

    def test_get_flat_dependencies(self):

        dependencies = self.evidence.get_flat_dependencies()
        self.assertIsNone(dependencies)

        dependencies = self.content.get_flat_dependencies()
        self.assertIn(self.fact, dependencies)
        self.assertIn(self.fiction, dependencies)
        self.assertIn(self.evidence, dependencies)
        self.assertIn(self.intuition, dependencies)
        self.assertEqual(dependencies.count(), 4)
        self.assertIsNone(self.content.get_saved_flat_dependencies())

        self.subtheory.delete()

        dependencies = self.content.get_flat_dependencies()
        self.assertIn(self.fact, dependencies)
        self.assertIn(self.fiction, dependencies)
        self.assertIn(self.intuition, dependencies)
        self.assertEqual(dependencies.count(), 3)
        self.assertIsNone(self.content.get_saved_flat_dependencies())

        dependencies = self.content.get_flat_dependencies(cache=True)
        self.assertIn(self.fact, dependencies)
        self.assertIn(self.fiction, dependencies)
        self.assertIn(self.intuition, dependencies)
        self.assertEqual(dependencies.count(), 3)
        self.assertIsNotNone(self.content.get_saved_flat_dependencies())

        dependencies = self.content.get_flat_dependencies(deleted=True)
        self.assertIn(self.fact, dependencies)
        self.assertIn(self.fiction, dependencies)
        self.assertIn(self.evidence, dependencies)
        self.assertIn(self.intuition, dependencies)
        self.assertEqual(dependencies.count(), 4)
        self.assertNotIn(self.evidence, self.content.dependencies.all())
        self.assertIsNotNone(self.content.get_saved_flat_dependencies())

    def test_get_theory_evidence(self):

        dependencies = self.evidence.get_theory_evidence()
        self.assertIsNone(dependencies)

        dependencies = self.content.get_theory_evidence()
        self.assertIn(self.fact, dependencies)
        self.assertIn(self.fiction, dependencies)
        self.assertEqual(dependencies.count(), 2)

        self.fiction.delete()

        dependencies = self.content.get_theory_evidence()
        self.assertIn(self.fact, dependencies)
        self.assertEqual(dependencies.count(), 1)

        dependencies = self.content.get_theory_evidence(deleted=True)
        self.assertIn(self.fact, dependencies)
        self.assertIn(self.fiction, dependencies)
        self.assertEqual(dependencies.count(), 2)

    def test_get_theory_subtheories(self):

        dependencies = self.evidence.get_theory_subtheories()
        self.assertIsNone(dependencies)

        dependencies = self.content.get_theory_subtheories()
        self.assertIn(self.subtheory, dependencies)
        self.assertEqual(dependencies.count(), 1)

        self.subtheory.delete()

        dependencies = self.content.get_theory_subtheories()
        self.assertEqual(dependencies.count(), 0)

        dependencies = self.content.get_theory_subtheories(deleted=True)
        self.assertIn(self.subtheory, dependencies)
        self.assertEqual(dependencies.count(), 1)

    def test_get_parent_theories01(self):

        dependencies = self.evidence.get_parent_theories()
        self.assertIn(self.subtheory, dependencies)
        self.assertEqual(dependencies.count(), 1)

        self.subtheory.delete()

        dependencies = self.evidence.get_parent_theories()
        self.assertEqual(dependencies.count(), 0)

        dependencies = self.evidence.get_parent_theories(deleted=True)
        self.assertIn(self.subtheory, dependencies)
        self.assertEqual(dependencies.count(), 1)

    def test_get_parent_theories02(self):

        dependencies = self.evidence.get_parent_theories(cache=True)
        self.assertIn(self.subtheory, dependencies)
        self.assertEqual(dependencies.count(), 1)

        dependencies = self.evidence.get_parent_theories(cache=True)
        self.assertIn(self.subtheory, dependencies)
        self.assertEqual(dependencies.count(), 1)

    def test_climb_theory_dependencies(self):
        new = get_or_create_subtheory(self.subtheory, true_title='new')
        dependencies = new.climb_theory_dependencies()
        self.assertIn(self.content, dependencies)
        self.assertIn(self.subtheory, dependencies)
        self.assertEqual(dependencies.count(), 2)

    def test_get_nested_dependencies(self):

        dependencies = self.evidence.get_nested_dependencies()
        self.assertIsNone(dependencies)

        dependencies = self.content.get_nested_dependencies()
        self.assertIn(self.fact, dependencies)
        self.assertIn(self.fiction, dependencies)
        self.assertIn(self.evidence, dependencies)
        self.assertIn(self.intuition, dependencies)
        self.assertIn(self.subtheory, dependencies)
        self.assertEqual(dependencies.count(), 5)

        self.subtheory.delete()

        dependencies = self.content.get_nested_dependencies()
        self.assertIn(self.fact, dependencies)
        self.assertIn(self.fiction, dependencies)
        self.assertIn(self.intuition, dependencies)
        self.assertEqual(dependencies.count(), 3)

        dependencies = self.content.get_nested_dependencies(deleted=True)
        self.assertIn(self.fact, dependencies)
        self.assertIn(self.fiction, dependencies)
        self.assertIn(self.evidence, dependencies)
        self.assertIn(self.intuition, dependencies)
        self.assertIn(self.subtheory, dependencies)
        self.assertEqual(dependencies.count(), 5)

    def test_get_nested_subtheory_dependencies(self):
        new = get_or_create_subtheory(self.subtheory, true_title='new')

        dependencies = self.evidence.get_nested_subtheory_dependencies()
        self.assertIsNone(dependencies)

        dependencies = self.content.get_nested_subtheory_dependencies()
        self.assertIn(self.subtheory, dependencies)
        self.assertIn(new, dependencies)
        self.assertEqual(dependencies.count(), 2)

        self.subtheory.delete()

        dependencies = self.content.get_nested_subtheory_dependencies()
        self.assertEqual(dependencies.count(), 0)

        dependencies = self.content.get_nested_subtheory_dependencies(deleted=True)
        self.assertIn(self.subtheory, dependencies)
        self.assertIn(new, dependencies)
        self.assertEqual(dependencies.count(), 2)

    def test_remove_dependency00(self):
        result = self.evidence.remove_dependency(self.intuition)
        self.assertFalse(result)
        # todo: test log

    def test_remove_dependency01(self):
        self.subtheory.remove_dependency(self.evidence)
        self.assertNotIn(self.evidence, self.subtheory.dependencies.all())
        self.assertNotIn(self.evidence, self.subtheory.flat_dependencies.all())
        self.assertNotIn(self.evidence, self.content.flat_dependencies.all())

    def test_remove_dependency02(self):
        self.content.add_dependency(self.evidence)
        self.content.refresh_from_db()
        self.subtheory.remove_dependency(self.evidence)
        self.assertNotIn(self.evidence, self.subtheory.dependencies.all())
        self.assertNotIn(self.evidence, self.subtheory.flat_dependencies.all())
        self.assertIn(self.evidence, self.content.dependencies.all())
        self.assertIn(self.evidence, self.content.flat_dependencies.all())

    def test_remove_dependency03(self):
        assert self.user.notifications.count() == 0
        self.content.remove_dependency(self.fiction, user=self.bob)
        self.assertEqual(self.user.notifications.count(), 1)

    def test_remove_flat_dependency(self):
        result = self.content.remove_flat_dependency(self.intuition)
        self.assertFalse(result)
        self.assertIn(self.intuition, self.content.get_flat_dependencies())

        result = self.content.remove_flat_dependency(self.evidence)
        self.assertFalse(result)
        self.assertIn(self.evidence, self.content.flat_dependencies.all())

        self.content.dependencies.remove(self.subtheory)
        result = self.content.remove_flat_dependency(self.evidence)
        self.assertTrue(result)
        self.assertNotIn(self.evidence, self.content.flat_dependencies.all())

    def test_get_opinions(self):

        opinions = self.evidence.get_opinions()
        self.assertEqual(opinions.count(), 0)

        opinions = self.content.get_opinions()
        self.assertEqual(opinions.count(), 1)
        self.assertIsNone(self.content.get_saved_opinions())

        opinions = self.content.get_opinions(cache=True)
        self.assertEqual(opinions.count(), 1)
        self.assertEqual(self.content.get_saved_opinions(), opinions)

        opinions = self.content.get_opinions(cache=True)
        self.assertEqual(opinions.count(), 1)
        self.assertEqual(self.content.get_saved_opinions(), opinions)

    def test_get_revisions(self):
        revisions = self.content.get_revisions()
        self.assertEqual(revisions.count(), 1)

    def test_get_intuition(self):
        dependencies = Content.objects.filter(title01='Intuition')
        self.assertEqual(dependencies.count(), 1)

        dependency = Content.get_intuition()
        dependencies = Content.objects.filter(title01='Intuition')
        self.assertTrue(dependency.is_evidence())
        self.assertFalse(dependency.is_fact())
        self.assertFalse(dependency.is_deleted())
        self.assertEqual(dependency.title01, 'Intuition')
        self.assertEqual(dependencies.count(), 1)

        dependency.delete(mode=DeleteMode.HARD)
        Content.INTUITION_PK += 1
        dependencies = Content.objects.filter(title01='Intuition')
        self.assertEqual(dependencies.count(), 1)

        super(Content, dependency).delete()
        dependency = Content.get_intuition(create=False)
        dependencies = Content.objects.filter(title01='Intuition')
        self.assertIsNone(dependency)
        self.assertEqual(dependencies.count(), 0)

        dependency = Content.get_intuition()
        dependencies = Content.objects.filter(title01='Intuition')
        self.assertTrue(dependency.is_evidence())
        self.assertFalse(dependency.is_fact())
        self.assertFalse(dependency.is_deleted())
        self.assertEqual(dependency.title01, 'Intuition')
        self.assertEqual(dependencies.count(), 1)

    def test_cache(self):
        assert self.content.get_saved_dependencies() is None
        assert self.content.get_saved_flat_dependencies() is None
        assert self.content.saved_stats is None

        result = self.evidence.cache()
        self.assertFalse(result)

        result = self.content.cache(dependencies=True, flat_dependencies=False)
        self.assertTrue(result)
        self.assertIsNotNone(self.content.get_saved_dependencies())
        self.assertIsNone(self.content.get_saved_flat_dependencies())
        self.assertIsNone(self.content.saved_stats)

        result = self.content.cache(dependencies=False, flat_dependencies=True)
        self.assertTrue(result)
        self.assertIsNotNone(self.content.get_saved_dependencies())
        self.assertIsNotNone(self.content.get_saved_flat_dependencies())
        self.assertIsNone(self.content.saved_stats)

        result = self.content.cache(dependencies=False, flat_dependencies=False)
        self.assertTrue(result)
        self.assertIsNotNone(self.content.get_saved_dependencies())
        self.assertIsNotNone(self.content.get_saved_flat_dependencies())

    def test_get_stats(self):

        stats = Stats.get(self.evidence, Stats.TYPE.ALL)
        self.assertIsNone(stats)

        stats = Stats.get(self.content, Stats.TYPE.ALL)
        self.assertIsNotNone(stats)

        stats = Stats.get(self.content, Stats.TYPE.ALL, cache=True)
        self.assertIsNotNone(stats)
        self.assertIsNotNone(self.content.saved_stats)

        self.assertEqual(self.content.stats.count(), 4)
        self.assertEqual(self.evidence.stats.count(), 0)

    def test_get_all_stats(self):
        assert self.content.saved_stats is None

        stats = Stats.get(self.content)
        self.assertEqual(stats.count(), 4)
        self.assertIsNone(self.content.saved_stats)

        stats = Stats.get(self.content, cache=True)
        self.assertEqual(stats.count(), 4)
        self.assertIsNotNone(self.content.saved_stats)

        stats = Stats.get(self.evidence)
        self.assertIsNone(stats)

    def test_update_hits(self):
        old_rank = self.content.rank
        old_hit_count = HitCount.objects.get_for_object(self.content)
        self.client.get(self.content.url())
        self.content.refresh_from_db()
        hit_count = HitCount.objects.get_for_object(self.content)
        self.assertEqual(hit_count.hits, old_hit_count.hits + 1)
        self.assertTrue(self.content.rank > old_rank)

    def test_update_activity_logs01(self):
        verb = "Created."
        self.subtheory.update_activity_logs(self.user, verb)
        self.assertEqual(self.subtheory.target_actions.count(), 1)
        self.assertEqual(self.content.target_actions.count(), 1)
        self.assertEqual(self.category.target_actions.count(), 1)
        self.assertEqual(self.bob.notifications.count(), 1)

        self.subtheory.update_activity_logs(self.user, verb)
        self.assertEqual(self.subtheory.target_actions.count(), 1)
        self.assertEqual(self.content.target_actions.count(), 1)
        self.assertEqual(self.category.target_actions.count(), 1)
        self.assertEqual(self.bob.notifications.count(), 1)

        action = self.subtheory.target_actions.first()
        action.timestamp -= datetime.timedelta(seconds=36000)
        action.save()

        action = self.content.target_actions.first()
        action.timestamp -= datetime.timedelta(seconds=36000)
        action.save()

        action = self.category.target_actions.first()
        action.timestamp -= datetime.timedelta(seconds=36000)
        action.save()

        notification = self.bob.notifications.first()
        notification.timestamp -= datetime.timedelta(seconds=36000)
        notification.save()

        self.subtheory.update_activity_logs(self.user, verb)
        self.assertEqual(self.subtheory.target_actions.count(), 2)
        self.assertEqual(self.content.target_actions.count(), 2)
        self.assertEqual(self.category.target_actions.count(), 2)
        self.assertEqual(self.bob.notifications.count(), 2)

    def test_update_activity_logs02(self):
        verb = "Deleted."
        self.subtheory.update_activity_logs(self.user, verb)
        self.assertEqual(self.subtheory.target_actions.count(), 1)
        self.assertEqual(self.content.target_actions.count(), 1)
        self.assertEqual(self.category.target_actions.count(), 1)
        self.assertEqual(self.bob.notifications.count(), 1)

    def test_delete00(self):
        hard_deleted = self.evidence.delete()
        self.assertFalse(hard_deleted)
        self.assertTrue(self.evidence.is_deleted())
        self.assertEqual(self.evidence.parent_flat_theories.count(), 0)

        hard_deleted = self.evidence.delete()
        self.assertFalse(hard_deleted)

    def test_delete01(self):
        self.evidence.delete()
        self.assertTrue(self.evidence.is_deleted())
        self.assertEqual(self.evidence.parent_flat_theories.count(), 0)

    def test_delete02(self):
        self.evidence.delete(mode=DeleteMode.HARD)
        self.assertIsNone(self.evidence.id)

    def test_delete03(self):
        self.subtheory.delete()
        self.evidence.refresh_from_db()
        self.assertTrue(self.subtheory.is_deleted())
        self.assertTrue(self.evidence.is_deleted())
        self.assertEqual(self.subtheory.parent_flat_theories.count(), 0)
        self.assertEqual(self.evidence.parent_flat_theories.count(), 0)

    def test_delete04(self):
        new = get_or_create_subtheory(self.content, true_title='new')
        new.add_dependency(self.evidence)
        self.subtheory.delete()
        self.evidence.refresh_from_db()
        self.assertTrue(self.subtheory.is_deleted())
        self.assertFalse(self.evidence.is_deleted())
        self.assertEqual(self.subtheory.parent_flat_theories.count(), 0)
        self.assertIn(self.evidence, new.get_dependencies())
        self.assertIn(self.evidence, self.subtheory.get_dependencies())
        self.assertEqual(self.evidence.get_parent_theories().count(), 1)

    def test_delete05(self):
        assert self.user.notifications.count() == 0

        self.fiction.delete(user=self.bob)
        self.assertEqual(self.user.notifications.count(), 1)

        self.content.delete(user=self.bob)
        self.assertEqual(self.user.notifications.count(), 4)

    def test_swap_titles00(self):
        self.evidence.title00 = 'False'
        swap_true_false(self.evidence)
        self.assertNotEqual(self.evidence.title01, 'False')

    def test_swap_titles01(self):
        self.content.title00 = 'False'
        swap_true_false(self.content)
        self.assertEqual(self.content.title01, 'False')
        self.assertEqual(self.user.notifications.count(), 1)
        # ToDo: test that points were reversed

    def test_convert00(self):
        success = convert_content_type(self.content)
        self.assertTrue(self.content.is_theory())
        self.assertFalse(success)

    def test_convert01(self):
        convert_content_type(self.subtheory)
        self.assertTrue(self.subtheory.is_evidence())
        self.assertFalse(self.subtheory.is_fact())
        # ToDo: lots...
        # ToDo: test notify

    def test_convert02(self):
        convert_content_type(self.subtheory, verifiable=True)
        self.assertTrue(self.subtheory.is_evidence())
        self.assertTrue(self.subtheory.is_fact())

    def test_convert03(self):
        convert_content_type(self.evidence)
        self.assertTrue(self.subtheory.is_subtheory())

    def test_merge00(self):
        result = merge_content(self.fact, self.fiction)
        self.assertFalse(result)
        # todo lots more

    def test_merge01(self):
        new = get_or_create_subtheory(self.content, true_title='new')
        assert new in self.content.get_dependencies()

    def test_recalculate_stats(self):

        result = Stats.recalculate(self.evidence)
        self.assertFalse(result)

        result = Stats.recalculate(self.content)
        self.assertTrue(result)
        # toDo lots more


# ************************************************************
# OpinionTests
#
#
#
#
#
#
#
#
# ************************************************************
class OpinionTests(TestCase):

    def setUp(self):

        # setup
        random.seed(0)
        create_groups_and_permissions()
        create_reserved_dependencies()
        create_categories()

        # create user(s)
        self.user = create_test_user(username='bob1', password='1234')
        self.bob = create_test_user(username='bob2', password='1234')

        # create data
        self.content = create_test_theory(created_by=self.user)
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
        self.intuition = self.content.get_intuition()

    def test_str(self):
        opinion = self.content.opinions.create(user=self.user)
        if opinion.is_true():
            self.assertEqual(opinion.__str__(), self.content.true_statement())
        else:
            self.assertEqual(opinion.__str__(), self.content.false_statement())

    def test_is_anonymous(self):
        # setup
        opinion = self.content.opinions.create(user=self.user)

        # Blah
        self.user.hidden = False
        opinion.anonymous = False
        self.assertFalse(opinion.is_anonymous())

        # Blah
        self.user.hidden = False
        opinion.anonymous = True
        self.assertTrue(opinion.is_anonymous())

        # Blah
        self.user.hidden = True
        opinion.anonymous = False
        self.assertTrue(opinion.is_anonymous())

        # Blah
        self.user.hidden = True
        opinion.anonymous = True
        self.assertTrue(opinion.is_anonymous())

    def test_get_owner(self):
        # setup
        opinion = self.content.opinions.create(user=self.user)

        # Blah
        self.user.hidden = False
        opinion.anonymous = False
        self.assertEqual(opinion.get_owner(), self.user.__str__())

        # Blah
        self.user.hidden = True
        opinion.anonymous = True
        self.assertEqual(opinion.get_owner(), 'Anonymous')

    def test_get_owner_long(self):
        # setup
        opinion = self.content.opinions.create(user=self.user)

        # Blah
        self.user.hidden = False
        opinion.anonymous = False
        self.assertIn(self.user.__str__(print_fullname=True), opinion.get_owner_long())

        # Blah
        self.user.hidden = True
        opinion.anonymous = True
        self.assertIn('Anonymous', opinion.get_owner_long())

    def test_edit_url(self):
        opinion = self.content.opinions.create(user=self.user)
        self.assertIsNotNone(opinion.edit_url())

    def test_compare_url(self):
        opinion = self.content.opinions.create(user=self.user)
        stats = Stats.get(self.content, Stats.TYPE.ALL)
        self.assertIsNotNone(get_compare_url(opinion))
        self.assertIsNotNone(get_compare_url(opinion, opinion))
        self.assertIsNotNone(get_compare_url(opinion, stats))

    def test_get_absolute_url(self):
        opinion = self.content.opinions.create(user=self.user)
        self.assertIsNotNone(opinion.get_absolute_url())

    def test_url(self):
        opinion = self.content.opinions.create(user=self.user)
        self.assertIsNotNone(opinion.url())

    def test_get_dependency(self):
        # setup
        opinion = self.content.opinions.create(user=self.user,)
        opinion.dependencies.create(
            content=self.fact,
            tt_input=100,
        )
        assert opinion.get_saved_dependencies() is None

        # Blah
        opinion_dependency = opinion.get_dependency(self.fact)
        self.assertIsNotNone(opinion_dependency)

        # Blah
        opinion_dependency = opinion.get_dependency(self.fiction)
        self.assertIsNone(opinion_dependency)

        # Blah
        opinion_dependency = opinion.get_dependency(self.fiction, create=True)
        self.assertIsNotNone(opinion_dependency)

    def test_get_dependency_cached(self):
        # setup
        opinion = self.content.opinions.create(user=self.user,)
        opinion.dependencies.create(
            content=self.fact,
            tt_input=100,
        )
        assert opinion.get_saved_dependencies() is None
        opinion.cache()

        # Blah
        opinion_dependency = opinion.get_dependency(self.fact)
        self.assertIsNotNone(opinion_dependency)

        # Blah
        opinion_dependency = opinion.get_dependency(self.fiction)
        self.assertIsNone(opinion_dependency)

        # Blah
        opinion_dependency = opinion.get_dependency(self.fiction, create=True)
        self.assertIsNotNone(opinion_dependency)

    def test_cache(self):
        # setup
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency = opinion.dependencies.create(
            content=self.fact,
            tt_input=100,
        )
        assert opinion.get_saved_dependencies() is None
        opinion.cache()

        self.assertEqual(opinion.get_saved_dependencies().count(), 1)
        self.assertIn(opinion_dependency, opinion.get_saved_dependencies())

    def test_get_dependencies(self):
        # setup
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency01 = opinion.dependencies.create(
            content=self.fact,
            tt_input=100,
        )
        opinion_dependency02 = opinion.dependencies.create(
            content=self.fiction,
            tt_input=100,
        )
        self.fiction.delete()
        assert opinion.get_saved_dependencies() is None

        # Blah
        dependencies = opinion.get_dependencies()
        self.assertEqual(dependencies.count(), 2)
        self.assertIn(opinion_dependency01, dependencies)
        self.assertIn(opinion_dependency02, dependencies)

        # Blah
        dependencies = opinion.get_dependencies(cache=True)
        self.assertIsNotNone(opinion.get_saved_dependencies())
        self.assertEqual(dependencies, opinion.get_saved_dependencies())
        self.assertEqual(dependencies.count(), 2)
        self.assertIn(opinion_dependency01, dependencies)
        self.assertIn(opinion_dependency02, dependencies)

    def test_get_flat_dependency(self):
        # setup
        opinion = self.content.opinions.create(user=self.user,)
        opinion.dependencies.create(
            content=self.fact,
            tt_input=100,
        )
        assert opinion.get_saved_flat_dependencies() is None

        # Blah
        opinion_dependency01 = opinion.get_flat_dependency(self.fact)
        opinion_dependency02 = opinion.get_flat_dependency(self.fact)
        self.assertEqual(opinion_dependency01, opinion_dependency02)

        # Blah
        opinion_dependency = opinion.get_flat_dependency(self.fact)
        self.assertIsNotNone(opinion_dependency)

        # Blah
        opinion_dependency = opinion.get_flat_dependency(self.fiction, create=False)
        self.assertIsNone(opinion_dependency)

        # Blah
        opinion_dependency = opinion.get_flat_dependency(self.fiction, create=True)
        self.assertIsNotNone(opinion_dependency)

    def test_get_flat_dependencies(self):
        # setup
        opinion = self.content.opinions.create(user=self.user,)
        opinion.dependencies.create(
            content=self.fact,
            ft_input=100,
        )
        opinion.dependencies.create(
            content=self.fiction,
            ft_input=100,
        )
        opinion.dependencies.create(
            content=self.subtheory,
            ft_input=100,
        )
        self.subtheory.opinions.create(user=self.user).dependencies.create(
            content=self.evidence,
            tt_input=100,
        )
        self.fiction.delete()

        # Blah
        flat_dependencies = opinion.get_flat_dependencies()
        self.assertEqual(flat_dependencies.count(), 4)
        self.assertIsNotNone(flat_dependencies.get(self.intuition.pk))
        self.assertIsNotNone(flat_dependencies.get(self.fact.pk))
        self.assertIsNotNone(flat_dependencies.get(self.fiction.pk))
        self.assertIsNotNone(flat_dependencies.get(self.evidence.pk))
        self.assertIsNone(flat_dependencies.get(self.subtheory.pk))

    def test_get_intuition(self):
        opinion = self.content.opinions.create(user=self.user)

        # Blah
        dependency = opinion.get_intuition(create=False)
        self.assertIsNone(dependency)

        # Blah
        dependency = opinion.get_intuition(create=True)
        self.assertIsNotNone(dependency)
        self.assertEqual(dependency.content, self.intuition)

    def test_get_theory_subtheories01(self):
        # setup
        opinion = self.content.opinions.create(user=self.user,)
        opinion.dependencies.create(
            content=self.fact,
            ft_input=100,
        )
        opinion.dependencies.create(
            content=self.subtheory,
            ft_input=100,
        )

        # Blah
        dependencies = opinion.get_theory_subtheories()
        self.assertEqual(dependencies.count(), 1)
        self.assertEqual(dependencies[0].content, self.subtheory)

        # Blah
        self.subtheory.delete()

        # Blah
        dependencies = opinion.get_theory_subtheories()
        self.assertEqual(dependencies.count(), 1)
        self.assertEqual(dependencies[0].content, self.subtheory)

    def test_get_theory_subtheories02(self):
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency01 = opinion.dependencies.create(
            content=self.fact,
            tt_input=100,
        )
        opinion_dependency02 = opinion.dependencies.create(
            content=self.subtheory,
            tt_input=100,
        )
        subtheories = opinion.get_theory_subtheories()
        self.assertEqual(subtheories.count(), 1)
        self.assertNotIn(opinion_dependency01, subtheories)
        self.assertIn(opinion_dependency02, subtheories)

    def test_get_theory_evidence01(self):
        # setup
        opinion = self.content.opinions.create(user=self.user,)
        opinion.dependencies.create(
            content=self.fact,
            ft_input=100,
        )
        opinion.dependencies.create(
            content=self.subtheory,
            ft_input=100,
        )

        # Blah
        dependencies = opinion.get_theory_evidence()
        self.assertEqual(dependencies.count(), 1)
        self.assertEqual(dependencies[0].content, self.fact)

        # Blah
        self.subtheory.delete()

        # Blah
        dependencies = opinion.get_theory_evidence()
        self.assertEqual(dependencies.count(), 1)
        self.assertEqual(dependencies[0].content, self.fact)

    def test_get_theory_evidence02(self):
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency01 = opinion.dependencies.create(
            content=self.fact,
            tt_input=100,
        )
        opinion_dependency02 = opinion.dependencies.create(
            content=self.subtheory,
            tt_input=100,
        )
        evidence = opinion.get_theory_evidence()
        self.assertEqual(evidence.count(), 1)
        self.assertIn(opinion_dependency01, evidence)
        self.assertNotIn(opinion_dependency02, evidence)

    def test_get_parent_opinions(self):
        # setup
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency = opinion.dependencies.create(
            content=self.subtheory,
            tt_input=80,
            ff_input=20,
        )
        child_opinion = self.subtheory.opinions.create(
            user=self.user,
            true_input=80,
            false_input=20,
            force=True,
        )

        # Blah
        parents = child_opinion.get_parent_opinions()
        self.assertEqual(parents.count(), 1)
        self.assertIn(opinion_dependency, parents)

    def test_update_points00(self):
        opinion = self.content.opinions.create(user=self.user,)
        opinion.update_points()
        intuition = opinion.get_intuition()
        self.assertEqual(intuition.true_points(), 0.0)
        self.assertEqual(intuition.false_points(), 0.0)
        self.assertEqual(opinion.true_points(), 0.0)
        self.assertEqual(opinion.false_points(), 0.0)

    def test_update_points01(self):
        opinion = self.content.opinions.create(
            user=self.user,
            true_input=100,
            false_input=0,
        )
        opinion.update_points()
        intuition = opinion.get_intuition()
        self.assertEqual(intuition.true_points(), 1.0)
        self.assertEqual(intuition.false_points(), 0.0)
        self.assertEqual(opinion.true_points(), 1.0)
        self.assertEqual(opinion.false_points(), 0.0)

    def test_update_points02(self):
        opinion = self.content.opinions.create(
            user=self.user,
            true_input=0,
            false_input=100,
        )
        opinion.update_points()
        intuition = opinion.get_intuition()
        self.assertEqual(intuition.true_points(), 0.0)
        self.assertEqual(intuition.false_points(), 1.0)
        self.assertEqual(opinion.true_points(), 0.0)
        self.assertEqual(opinion.false_points(), 1.0)

    def test_update_points03(self):
        opinion = self.content.opinions.create(
            user=self.user,
            true_input=50,
            false_input=50,
        )
        opinion.update_points()
        intuition = opinion.get_intuition()
        self.assertEqual(intuition.true_points(), 0.5)
        self.assertEqual(intuition.false_points(), 0.5)
        self.assertEqual(opinion.true_points(), 0.5)
        self.assertEqual(opinion.false_points(), 0.5)

    def test_update_points04(self):
        # setup
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency = opinion.dependencies.create(content=self.fact,)
        opinion.update_points()

        # Blah
        dependencies = opinion.get_dependencies()
        self.assertNotIn(opinion_dependency, dependencies)

    def test_update_points_fact01(self):
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency = opinion.dependencies.create(
            content=self.fact,
            tt_input=100,
        )
        opinion.update_points()
        opinion_dependency.refresh_from_db()
        intuition = opinion.get_intuition()
        self.assertEqual(intuition.true_points(), 0.0)
        self.assertEqual(intuition.false_points(), 0.0)
        self.assertEqual(opinion_dependency.true_points(), 1.0)
        self.assertEqual(opinion_dependency.false_points(), 0.0)
        self.assertEqual(opinion.true_points(), 1.0)
        self.assertEqual(opinion.false_points(), 0.0)

    def test_update_points_fact02(self):
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency = opinion.dependencies.create(
            content=self.fact,
            tf_input=100,
        )
        opinion.update_points()
        opinion_dependency.refresh_from_db()
        intuition = opinion.get_intuition()
        self.assertEqual(intuition.true_points(), 0.0)
        self.assertEqual(intuition.false_points(), 0.0)
        self.assertEqual(opinion_dependency.true_points(), 0.0)
        self.assertEqual(opinion_dependency.false_points(), 1.0)
        self.assertEqual(opinion.true_points(), 0.0)
        self.assertEqual(opinion.false_points(), 1.0)

    def test_update_points_fact03(self):
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency = opinion.dependencies.create(
            content=self.fact,
            tt_input=100,
            tf_input=100,
        )
        opinion.update_points()
        opinion_dependency.refresh_from_db()
        intuition = opinion.get_intuition()
        self.assertEqual(intuition.true_points(), 0.0)
        self.assertEqual(intuition.false_points(), 0.0)
        self.assertEqual(opinion_dependency.true_points(), 0.5)
        self.assertEqual(opinion_dependency.false_points(), 0.5)
        self.assertEqual(opinion.true_points(), 0.5)
        self.assertEqual(opinion.false_points(), 0.5)

    def test_update_points_fact10(self):
        opinion = self.content.opinions.create(
            user=self.user,
            true_input=50,
        )
        opinion_dependency = opinion.dependencies.create(
            content=self.fact,
            tf_input=50,
        )
        opinion.update_points()
        opinion_dependency.refresh_from_db()
        intuition = opinion.get_intuition()
        self.assertEqual(intuition.true_points(), 0.5)
        self.assertEqual(intuition.false_points(), 0.0)
        self.assertEqual(opinion_dependency.true_points(), 0.0)
        self.assertEqual(opinion_dependency.false_points(), 0.5)
        self.assertEqual(opinion.true_points(), 0.5)
        self.assertEqual(opinion.false_points(), 0.5)

    def test_update_points_fact11(self):
        opinion = self.content.opinions.create(
            user=self.user,
            true_input=25,
            false_input=75,
            force=True,
        )
        opinion_dependency = opinion.dependencies.create(
            content=self.fact,
            tf_input=50,
        )
        opinion.update_points()
        opinion_dependency.refresh_from_db()
        intuition = opinion.get_intuition()
        self.assertEqual(intuition.true_points(), 0.25)
        self.assertEqual(intuition.false_points(), 0.0)
        self.assertEqual(opinion_dependency.true_points(), 0.0)
        self.assertEqual(opinion_dependency.false_points(), 0.75)
        self.assertEqual(opinion.true_points(), 0.25)
        self.assertEqual(opinion.false_points(), 0.75)

    def test_update_points_subtheory01(self):
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency = opinion.dependencies.create(
            content=self.subtheory,
            tt_input=100,
        )
        opinion.update_points()
        opinion_dependency.refresh_from_db()
        flat_intuition = opinion.get_flat_dependency(content=self.intuition)
        self.assertEqual(flat_intuition.true_points(), 1.0)
        self.assertEqual(flat_intuition.false_points(), 0.0)
        self.assertEqual(opinion_dependency.true_points(), 1.0)
        self.assertEqual(opinion_dependency.false_points(), 0.0)
        self.assertEqual(opinion.true_points(), 1.0)
        self.assertEqual(opinion.false_points(), 0.0)

    def test_update_points_subtheory02(self):
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency = opinion.dependencies.create(
            content=self.subtheory,
            tf_input=100,
        )
        opinion.update_points()
        opinion_dependency.refresh_from_db()
        flat_intuition = opinion.get_flat_dependency(content=self.intuition)
        self.assertEqual(flat_intuition.true_points(), 0.0)
        self.assertEqual(flat_intuition.false_points(), 1.0)
        self.assertEqual(opinion_dependency.true_points(), 0.0)
        self.assertEqual(opinion_dependency.false_points(), 1.0)
        self.assertEqual(opinion.true_points(), 0.0)
        self.assertEqual(opinion.false_points(), 1.0)

    def test_update_points_subtheory10(self):
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency = opinion.dependencies.create(
            content=self.subtheory,
            tt_input=100,
        )
        child_opinion = self.subtheory.opinions.create(user=self.user,)
        child_opinion.update_points()
        opinion.update_points()
        opinion_dependency.refresh_from_db()
        flat_intuition = opinion.get_flat_dependency(content=self.intuition)
        self.assertEqual(flat_intuition.true_points(), 1.0)
        self.assertEqual(flat_intuition.false_points(), 0.0)
        self.assertEqual(opinion_dependency.true_points(), 1.0)
        self.assertEqual(opinion_dependency.false_points(), 0.0)
        self.assertEqual(opinion.true_points(), 1.0)
        self.assertEqual(opinion.false_points(), 0.0)

    def test_update_points_subtheory11(self):
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency = opinion.dependencies.create(
            content=self.subtheory,
            tf_input=100,
        )
        child_opinion = self.subtheory.opinions.create(user=self.user,)
        child_opinion.update_points()
        opinion.update_points()
        opinion_dependency.refresh_from_db()
        flat_intuition = opinion.get_flat_dependency(content=self.intuition)
        self.assertEqual(flat_intuition.true_points(), 0.0)
        self.assertEqual(flat_intuition.false_points(), 1.0)
        self.assertEqual(opinion_dependency.true_points(), 0.0)
        self.assertEqual(opinion_dependency.false_points(), 1.0)
        self.assertEqual(opinion.true_points(), 0.0)
        self.assertEqual(opinion.false_points(), 1.0)

    def test_update_points_subtheory20(self):
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency = opinion.dependencies.create(
            content=self.subtheory,
            ft_input=100,
        )
        child_opinion = self.subtheory.opinions.create(user=self.user,)
        child_dependency = child_opinion.dependencies.create(
            content=self.evidence,
            tt_input=100,
        )
        child_opinion.update_points()
        opinion.update_points()
        opinion_dependency.refresh_from_db()
        child_dependency.refresh_from_db()
        flat_intuition = opinion.get_flat_dependency(content=self.intuition)
        self.assertEqual(flat_intuition.true_points(), 1.0)
        self.assertEqual(flat_intuition.false_points(), 0.0)
        self.assertEqual(opinion_dependency.true_points(), 1.0)
        self.assertEqual(opinion_dependency.false_points(), 0.0)
        self.assertEqual(opinion.true_points(), 1.0)
        self.assertEqual(opinion.false_points(), 0.0)

    def test_update_points_subtheory21(self):
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency = opinion.dependencies.create(
            content=self.subtheory,
            tt_input=100,
        )
        child_opinion = self.subtheory.opinions.create(user=self.user,)
        child_dependency = child_opinion.dependencies.create(
            content=self.evidence,
            tt_input=100,
        )
        child_opinion.update_points()
        opinion.update_points()
        opinion_dependency.refresh_from_db()
        child_dependency.refresh_from_db()
        flat_intuition = opinion.get_flat_dependency(content=self.intuition)
        self.assertEqual(flat_intuition.true_points(), 0.0)
        self.assertEqual(flat_intuition.false_points(), 0.0)
        self.assertEqual(opinion_dependency.true_points(), 1.0)
        self.assertEqual(opinion_dependency.false_points(), 0.0)
        self.assertEqual(opinion.true_points(), 1.0)
        self.assertEqual(opinion.false_points(), 0.0)

    def test_update_points_subtheory22(self):
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency = opinion.dependencies.create(
            content=self.subtheory,
            tt_input=80,
            tf_input=20,
        )
        child_opinion = self.subtheory.opinions.create(
            user=self.user,
            true_input=80,
            false_input=20,
            force=True,
        )
        child_dependency = child_opinion.dependencies.create(
            content=self.evidence,
            tt_input=100,
        )
        child_opinion.update_points()
        opinion.update_points()
        opinion_dependency.refresh_from_db()
        child_dependency.refresh_from_db()

        flat_intuition = child_opinion.get_flat_dependency(content=self.intuition)
        self.assertEqual(child_opinion.true_points(), 0.8)
        self.assertEqual(child_opinion.false_points(), 0.2)
        self.assertEqual(flat_intuition.true_points(), 0.0)
        self.assertEqual(flat_intuition.false_points(), 0.2)
        self.assertEqual(child_dependency.true_points(), 0.8)
        self.assertEqual(child_dependency.false_points(), 0.0)

        flat_intuition = opinion.get_flat_dependency(content=self.intuition)
        flat_evidence = opinion.get_flat_dependency(content=self.evidence)
        self.assertEqual(opinion_dependency.true_points(), 0.8)
        self.assertEqual(opinion_dependency.false_points(), 0.2)
        self.assertEqual(flat_intuition.true_points(), 0.0)
        self.assertEqual(flat_intuition.false_points(), 0.0)
        self.assertEqual(flat_evidence.true_points(), 0.8)
        self.assertEqual(flat_evidence.false_points(), 0.2)
        self.assertEqual(opinion.true_points(), 0.8)
        self.assertEqual(opinion.false_points(), 0.2)

    def test_update_points_subtheory23(self):
        opinion = self.content.opinions.create(user=self.user,)
        opinion_dependency = opinion.dependencies.create(
            content=self.subtheory,
            tt_input=80,
            ff_input=20,
        )
        child_opinion = self.subtheory.opinions.create(
            user=self.user,
            true_input=80,
            false_input=20,
            force=True,
        )
        child_dependency = child_opinion.dependencies.create(
            content=self.evidence,
            tt_input=100,
        )
        child_opinion.update_points()
        opinion.update_points()
        opinion_dependency.refresh_from_db()
        child_dependency.refresh_from_db()

        flat_intuition = child_opinion.get_flat_dependency(content=self.intuition)
        self.assertEqual(child_opinion.true_points(), 0.8)
        self.assertEqual(child_opinion.false_points(), 0.2)
        self.assertEqual(flat_intuition.true_points(), 0.0)
        self.assertEqual(flat_intuition.false_points(), 0.2)
        self.assertEqual(child_dependency.true_points(), 0.8)
        self.assertEqual(child_dependency.false_points(), 0.0)

        flat_intuition = opinion.get_flat_dependency(content=self.intuition)
        flat_evidence = opinion.get_flat_dependency(content=self.evidence)
        self.assertEqual(opinion_dependency.true_points(), 0.8)
        self.assertEqual(opinion_dependency.false_points(), 0.2)
        self.assertEqual(flat_intuition.true_points(), 0.0)
        self.assertEqual(flat_intuition.false_points(), 0.2)
        self.assertEqual(flat_evidence.true_points(), 0.8)
        self.assertEqual(flat_evidence.false_points(), 0.0)
        self.assertEqual(opinion.true_points(), 0.8)
        self.assertEqual(opinion.false_points(), 0.2)

    def test_copy(self):
        # setup existing opinion
        opinion = self.content.opinions.create(
            user=self.user,
            true_input=10,
            false_input=20,
        )
        opinion_dependency = opinion.dependencies.create(
            content=self.subtheory,
            tt_input=80,
            ff_input=20,
        )
        child_opinion = self.subtheory.opinions.create(
            user=self.user,
            true_input=80,
            false_input=20,
            force=True,
        )
        child_opinion.dependencies.create(
            content=self.evidence,
            tt_input=100,
        )
        opinion.update_points()
        child_opinion.update_points()

        # setup bob's opinion
        opinion = self.content.opinions.create(
            user=self.bob,
            true_input=44,
            false_input=55,
        )
        opinion_dependency = opinion.dependencies.create(
            content=self.subtheory,
            tt_input=66,
            ff_input=33,
        )
        child_opinion = self.subtheory.opinions.create(
            user=self.bob,
            true_input=99,
            false_input=22,
            force=True,
        )
        child_opinion.dependencies.create(
            content=self.evidence,
            ff_input=100,
        )
        opinion.update_points()
        child_opinion.update_points()

        # Blah
        copied_opinion = copy_opinion(opinion, self.user)
        copied_dependency = copied_opinion.get_dependencies().get(
            content=opinion_dependency.content)
        copied_child = get_or_none(self.subtheory.get_opinions(), user=self.user)
        self.assertEqual(copied_opinion.true_points(), opinion.true_points())
        self.assertEqual(copied_dependency.tt_input, opinion_dependency.tt_input)
        self.assertEqual(copied_dependency.ff_input, opinion_dependency.ff_input)
        self.assertNotEqual(copied_child.true_points(), child_opinion.true_points())

        # Blah
        copied_opinion = copy_opinion(opinion, self.user, recursive=True)
        copied_dependency = copied_opinion.get_dependencies().get(
            content=opinion_dependency.content)
        copied_child = get_or_none(self.subtheory.get_opinions(), user=self.user)
        self.assertEqual(copied_opinion.true_points(), opinion.true_points())
        self.assertEqual(copied_dependency.tt_input, opinion_dependency.tt_input)
        self.assertEqual(copied_dependency.ff_input, opinion_dependency.ff_input)
        self.assertEqual(copied_child.true_points(), child_opinion.true_points())

    def test_true_points(self):
        # setup
        opinion = self.content.opinions.create(user=self.user,)
        opinion.dependencies.create(
            content=self.subtheory,
            tt_input=80,
            ff_input=20,
        )
        opinion.update_points()

        # Blah
        self.assertEqual(opinion.true_points(), 0.8)

        # coverage test
        opinion.true_total = 0
        opinion.false_total = 0
        self.assertEqual(opinion.true_points(), 0.0)

        # coverage test
        opinion.true_total = 0
        opinion.false_total = 0
        opinion.force = True
        self.assertEqual(opinion.true_points(), 0.0)

        # ToDo: Much more

    def test_false_points(self):
        # setup
        opinion = self.content.opinions.create(user=self.user,)
        opinion.dependencies.create(
            content=self.subtheory,
            tt_input=80,
            ff_input=20,
        )
        opinion.update_points()

        # Blah
        self.assertEqual(opinion.false_points(), 0.2)

        # coverage test
        opinion.true_total = 0
        opinion.false_total = 0
        self.assertEqual(opinion.false_points(), 0.0)

        # coverage test
        opinion.true_total = 0
        opinion.false_total = 0
        opinion.force = True
        self.assertEqual(opinion.false_points(), 0.0)

        # ToDo: Much more

    def test_swap_true_false(self):
        # setup
        opinion = self.content.opinions.create(
            user=self.user,
            true_input=80,
            false_input=20,
        )
        opinion.dependencies.create(
            content=self.subtheory,
            tt_input=80,
            ff_input=20,
        )
        opinion.update_points()
        opinion.swap_true_false()

        # Blah
        self.assertEqual(opinion.true_input, 20)
        self.assertEqual(opinion.false_input, 80)
        self.assertEqual(opinion.true_points(), 0.2)
        self.assertEqual(opinion.false_points(), 0.8)

        # ToDo: much more

    def test_update_hits(self):
        # setup
        opinion = self.content.opinions.create(user=self.user)
        hit_count = HitCount.objects.get_for_object(opinion)
        assert hit_count.hits == 0

        # Blah
        url = reverse('theories:opinion-analysis',
                      kwargs={
                          'content_pk': opinion.content.pk,
                          'opinion_pk': opinion.pk
                      })
        self.client.get(url)
        hit_count = HitCount.objects.get_for_object(opinion)
        self.assertEqual(hit_count.hits, 1)

    def test_update_activity_logs(self):
        # setup
        opinion = self.content.opinions.create(user=self.user)
        follow(self.bob, opinion, send_action=False)
        assert self.bob.notifications.count() == 0
        assert opinion.target_actions.count() == 0

        # Blah
        verb = "Modified."
        opinion.update_activity_logs(self.user, verb)
        self.assertEqual(opinion.target_actions.count(), 1)
        self.assertEqual(self.bob.notifications.count(), 1)

        # ToDo: Much more


# ************************************************************
# OpinionDependencyTests
#
#
#
#
#
#
# ************************************************************
class OpinionDependencyTests(TestCase):

    def setUp(self):

        # setup
        random.seed(0)
        create_groups_and_permissions()
        create_reserved_dependencies()
        create_categories()

        # create user(s)
        self.user = create_test_user(username='not_bob', password='1234')
        self.bob = create_test_user(username='bob', password='1234')

        # create data
        self.content = create_test_theory(created_by=self.user)
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
        self.opinion = create_test_opinion(content=self.content, user=self.user, dependencies=True)
        self.sub_opinion = create_test_opinion(content=self.subtheory,
                                               user=self.user,
                                               dependencies=True)
        self.stats = Stats.get(self.content, Stats.TYPE.ALL)
        self.opinion_dependency = self.opinion.get_dependency(self.fact)

    def test_get_absolute_url(self):
        # Blah
        opinion_dependency = self.opinion.get_dependency(self.fact)
        self.assertIsNone(opinion_dependency.get_absolute_url())

        # Blah
        opinion_dependency = self.opinion.get_dependency(self.subtheory)
        self.assertIsNotNone(opinion_dependency.get_absolute_url())

    def test_url(self):
        # Blah
        opinion_dependency = self.opinion.get_dependency(self.fact)
        self.assertIsNone(opinion_dependency.get_absolute_url())

        # Blah
        opinion_dependency = self.opinion.get_dependency(self.subtheory)
        self.assertIsNotNone(opinion_dependency.get_absolute_url())

    def test_get_root(self):
        # Blah
        opinion_dependency = self.opinion.get_dependency(self.fact)
        self.assertIsNone(opinion_dependency.get_root())

        # Blah
        opinion_dependency = self.opinion.get_dependency(self.subtheory)
        self.assertEqual(opinion_dependency.get_root(), self.sub_opinion)

    def test_tt_points(self):
        self.opinion_dependency.tt_points()
        # ToDo: more

    def test_tf_points(self):
        self.opinion_dependency.tf_points()
        # ToDo: more

    def test_ft_points(self):
        self.opinion_dependency.ft_points()
        # ToDo: more

    def test_ff_points(self):
        self.opinion_dependency.ff_points()
        # ToDo: more

    def test_true_points(self):
        self.opinion_dependency.true_points()
        # ToDo: more

    def test_false_points(self):
        self.opinion_dependency.false_points()
        # ToDo: more

    def test_is_deleted(self):

        # Blah
        opinion_dependency = self.opinion.get_dependency(self.fact)
        self.assertFalse(opinion_dependency.is_deleted())

        # Blah
        self.fact.delete()
        opinion_dependency = self.opinion.get_dependency(self.fact)
        self.assertTrue(opinion_dependency.is_deleted())

        # Blah
        self.content.remove_dependency(self.fiction)
        opinion_dependency = self.opinion.get_dependency(self.fiction)
        self.assertTrue(opinion_dependency.is_deleted())


# ************************************************************
# Stats Model Tests
#
#
#
#
#
#
#
#
# ************************************************************
class StatsTests(TestCase):

    def setUp(self):

        # setup
        random.seed(0)
        create_groups_and_permissions()
        create_reserved_dependencies()
        create_categories()

        # create user(s)
        self.user = create_test_user(username='not_bob', password='1234')
        self.bob = create_test_user(username='bob', password='1234')

        # create data
        self.content = create_test_theory(created_by=self.user)
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
        self.opinion = create_test_opinion(content=self.content, user=self.user, dependencies=True)
        self.stats = Stats.get(self.content, Stats.TYPE.ALL)

    def test_str(self):
        self.assertIsNotNone(self.stats.__str__())

    def test_initialize(self):
        for stats in Stats.get(self.content):
            stats.delete()
        assert self.content.stats.count() == 0

        # Blah
        Stats.initialize(self.content)
        stats = Stats.get(self.content)
        self.assertEqual(stats.count(), 4)

    def test_get_slug(self):
        self.assertEqual(Stats.type_to_slug(Stats.TYPE.ALL), 'all')

    def test_slug(self):
        self.assertEqual(self.stats.get_slug(), 'all')

    def test_get_owner(self):
        # Blah
        self.assertEqual(self.stats.get_owner(), 'Everyone')

        # coverage
        for stats in Stats.get(self.content):
            stats.get_owner()

    def test_get_owner_long(self):
        # Blah
        self.assertIn('Everyone', self.stats.get_owner_long())

        # coverage
        for stats in Stats.get(self.content):
            stats.get_owner_long()

    def test_point_range(self):
        # Blah
        self.assertEqual(self.stats.get_point_range(), (0.0, 1.0))

        # coverage
        for stats in Stats.get(self.content):
            stats.get_point_range()

    def test_get_dependency(self):
        # Blah
        stats_dependency = self.stats.get_dependency(self.fact)
        self.assertIsNotNone(stats_dependency)

        # Blah
        stats_dependency = self.stats.get_dependency(self.evidence, create=False)
        self.assertIsNone(stats_dependency)

        # Blah
        stats_dependency = self.stats.get_dependency(self.evidence, create=True)
        self.assertIsNotNone(stats_dependency)

    def test_get_dependencies(self):
        # Blah
        dependencies = self.stats.get_dependencies(cache=False)
        self.assertEqual(dependencies.count(), 4)
        self.assertIsNone(self.stats.get_saved_dependencies())

        # Blah
        dependencies = self.stats.get_dependencies(cache=True)
        self.assertEqual(dependencies.count(), 4)
        self.assertIsNotNone(self.stats.get_saved_dependencies())

    def test_get_flat_dependency(self):
        # Blah
        stats_dependency = self.stats.get_flat_dependency(self.fact)
        self.assertIsNotNone(stats_dependency)

        # Blah
        stats_dependency = self.stats.get_flat_dependency(self.evidence, create=False)
        self.assertIsNone(stats_dependency)

        # Blah
        stats_dependency = self.stats.get_flat_dependency(self.evidence, create=True)
        self.assertIsNotNone(stats_dependency)

        # Blah
        stats_dependency01 = self.stats.get_flat_dependency(self.evidence, create=True)
        stats_dependency02 = self.stats.get_flat_dependency(self.evidence, create=True)
        self.assertEqual(stats_dependency01, stats_dependency02)

    def test_get_flat_dependencies(self):
        # Blah
        dependencies = self.stats.get_flat_dependencies(cache=False)
        self.assertEqual(dependencies.count(), 3)
        self.assertIsNone(self.stats.get_saved_flat_dependencies())

        # Blah
        dependencies = self.stats.get_flat_dependencies(cache=True)
        self.assertEqual(dependencies.count(), 3)
        self.assertIsNotNone(self.stats.get_saved_flat_dependencies())

    def test_add_opinion(self):
        # setup
        opinion = self.content.opinions.create(user=self.bob,)
        opinion_dependency = opinion.dependencies.create(
            content=self.fact,
            tt_input=20,
            tf_input=80,
        )
        self.stats.reset()
        opinion.update_points()
        assert self.stats.opinions.count() == 0

        # Blah
        self.stats.add_opinion(opinion)
        self.assertEqual(self.stats.opinions.count(), 1)

    def test_remove_opinion(self):
        self.stats.remove_opinion(self.opinion)
        self.assertEqual(self.stats.opinions.count(), 0)
        self.assertEqual(self.stats.true_points(), 0.0)
        self.assertEqual(self.stats.false_points(), 0.0)
        # ToDo: more

    def test_cache(self):
        assert self.stats.get_saved_dependencies() is None
        assert self.stats.get_saved_flat_dependencies() is None

        # Blah
        self.stats.cache(lazy=True)
        self.assertEqual(self.stats.get_saved_dependencies().count(), 0)
        self.assertEqual(self.stats.get_saved_flat_dependencies().count(), 0)

        # Blah
        self.stats.saved_dependencies = None
        self.stats.saved_flat_dependencies = None
        self.stats.cache(lazy=False)
        self.assertEqual(self.stats.get_saved_dependencies().count(), 4)
        self.assertEqual(self.stats.get_saved_flat_dependencies().count(), 3)

    def test_save_changes(self):
        # setup
        true_points = self.stats.true_points()
        false_points = self.stats.false_points()
        assert true_points > 0
        assert false_points > 0

        # Blah
        self.stats.reset(save=False)
        self.stats.refresh_from_db()
        self.assertEqual(self.stats.true_points(), true_points)
        self.assertEqual(self.stats.false_points(), false_points)

        # Blah
        self.stats.reset(save=False)
        self.stats.save_changes()
        self.stats.refresh_from_db()
        self.assertEqual(self.stats.true_points(), 0.0)
        self.assertEqual(self.stats.false_points(), 0.0)

        # ToDo: more

    def test_total_points(self):
        # setup
        opinion = self.content.opinions.create(user=self.bob,)
        opinion_dependency = opinion.dependencies.create(
            content=self.fact,
            tt_input=20,
            tf_input=80,
        )
        self.stats.reset()
        opinion.update_points()
        self.stats.add_opinion(opinion)

        # Blah
        self.assertEqual(self.stats.total_points(), 1.0)

    def test_true_points(self):
        # setup
        opinion = self.content.opinions.create(user=self.bob,)
        opinion_dependency = opinion.dependencies.create(
            content=self.fact,
            tt_input=20,
            tf_input=80,
        )
        self.stats.reset()
        opinion.update_points()
        self.stats.add_opinion(opinion)

        # Blah
        self.assertEqual(self.stats.true_points(), 0.20)

    def test_false_points(self):
        # setup
        opinion = self.content.opinions.create(user=self.bob,)
        opinion_dependency = opinion.dependencies.create(
            content=self.fact,
            tt_input=20,
            tf_input=80,
        )
        self.stats.reset()
        opinion.update_points()
        self.stats.add_opinion(opinion)

        # Blah
        self.assertEqual(self.stats.false_points(), 0.80)

    def test_swap_true_false(self):
        # setup
        true_points = self.stats.true_points()
        false_points = self.stats.false_points()
        assert true_points != false_points

        # Blah
        self.stats.swap_true_false()
        self.assertEqual(self.stats.true_points(), false_points)
        self.assertEqual(self.stats.false_points(), true_points)

        # ToDo: more

    def test_reset(self):
        assert self.stats.true_points() != 0
        assert self.stats.false_points() != 0
        self.stats.reset()
        self.assertEqual(self.stats.true_points(), 0)
        self.assertEqual(self.stats.false_points(), 0)
        # ToDo: test save

    def test_opinion_is_member(self):
        self.assertTrue(self.stats.opinion_is_member(self.opinion))

    def test_get_opinions(self):
        self.assertIn(self.opinion, self.stats.get_opinions())

    def test_url(self):
        self.assertIsNotNone(self.stats.url())

    def test_compare_url(self):
        self.assertIsNotNone(get_compare_url(self.stats))


# ************************************************************
# StatsDependencyTests
#
#
#
#
#
#
# ************************************************************
class StatsDependencyTests(TestCase):

    def setUp(self):

        # setup
        random.seed(0)
        create_groups_and_permissions()
        create_reserved_dependencies()
        create_categories()

        # create user(s)
        self.user = create_test_user(username='not_bob', password='1234')
        self.bob = create_test_user(username='bob', password='1234')

        # create data
        self.content = create_test_theory(created_by=self.user)
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
        self.opinion = create_test_opinion(content=self.content, user=self.user, dependencies=True)
        self.stats = Stats.get(self.content, Stats.TYPE.ALL)
        self.stats_dependency = self.stats.get_dependency(self.fact)

    def test_url(self):
        # Blah
        stats_dependency = self.stats.get_dependency(self.fact)
        self.assertIsNotNone(stats_dependency.url())

        # Blah
        stats_dependency = self.stats.get_dependency(self.subtheory)
        self.assertIsNotNone(stats_dependency.url())

    def test_get_root(self):
        # Blah
        stats_dependency = self.stats.get_dependency(self.fact)
        self.assertIsNone(stats_dependency.get_root())

        # Blah
        stats_dependency = self.stats.get_dependency(self.subtheory)
        self.assertIsNotNone(stats_dependency.get_root())

    def test_true_points(self):
        self.stats_dependency.true_points()
        # ToDo: more

    def test_false_points(self):
        self.stats_dependency.false_points()
        # ToDo: more

    def test_total_points(self):
        self.stats_dependency.total_points()
        # ToDo: more

    def test_reset(self, save=True):
        assert self.stats_dependency.true_points() != 0.0
        assert self.stats_dependency.false_points() != 0.0
        self.stats_dependency.reset()
        self.assertEqual(self.stats_dependency.true_points(), 0.0)
        self.assertEqual(self.stats_dependency.false_points(), 0.0)


# ************************************************************
# StatsFlatDependencyTests
#
#
#
#
#
#
# ************************************************************
class StatsFlatDependencyTests(TestCase):

    def setUp(self):

        # setup
        random.seed(0)
        create_groups_and_permissions()
        create_reserved_dependencies()
        create_categories()

        # create user(s)
        self.user = create_test_user(username='not_bob', password='1234')
        self.bob = create_test_user(username='bob', password='1234')

        # create data
        self.content = create_test_theory(created_by=self.user)
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
        self.opinion = create_test_opinion(content=self.content, user=self.user, dependencies=True)
        self.stats = Stats.get(self.content, Stats.TYPE.ALL)
        self.stats_dependency = self.stats.get_flat_dependency(self.fact)

    def test_url(self):
        stats_dependency = self.stats.get_flat_dependency(self.fact)
        self.assertIsNotNone(stats_dependency.url())

    def test_get_root(self):
        stats_dependency = self.stats.get_flat_dependency(self.fact)
        self.assertIsNone(stats_dependency.get_root())

    def test_true_points(self):
        self.stats_dependency.true_points()
        # ToDo: more

    def test_false_points(self):
        self.stats_dependency.false_points()
        # ToDo: more

    def test_total_points(self):
        self.stats_dependency.total_points()
        # ToDo: more

    def test_reset(self, save=True):
        assert self.stats_dependency.true_points() != 0.0
        assert self.stats_dependency.false_points() != 0.0
        self.stats_dependency.reset()
        self.assertEqual(self.stats_dependency.true_points(), 0.0)
        self.assertEqual(self.stats_dependency.false_points(), 0.0)


# ************************************************************
# OpinionBaseTests
#
#
#
#
#
#
#
# ************************************************************
class OpinionBaseTests(TestCase):

    def setUp(self):

        # setup
        random.seed(0)
        create_groups_and_permissions()
        create_reserved_dependencies()
        create_categories()

        # create user(s)
        self.user = create_test_user(username='not_bob', password='1234')
        self.bob = create_test_user(username='bob', password='1234')

        # create data
        self.content = create_test_theory(created_by=self.user)
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
        self.opinion = create_test_opinion(content=self.content, user=self.user, dependencies=True)
        self.stats = Stats.get(self.content, Stats.TYPE.ALL)
        self.stats_dependency = self.stats.get_flat_dependency(self.fact)

    def test_create(self):
        pass

    def test_check_data(self):
        pass

    def test_str(self):
        pass

    def test_url(self):
        pass

    def test_compare_url(self):
        pass

    def test_get_dependencies(self):
        pass

    def test_get_flat_dependencies(self):
        pass

    def test_get_point_distribution(self):
        pass

    def test_true_points(self):
        pass

    def test_false_points(self):
        pass

    def test_is_true(self):
        pass

    def test_is_false(self):
        pass

    def test_get_point_range(self):
        pass


# ************************************************************
# OpinionDependencyBaseTests
#
#
#
#
#
#
#
# ************************************************************
class OpinionDependencyBaseTests(TestCase):

    def setUp(self):

        # setup
        random.seed(0)
        create_groups_and_permissions()
        create_reserved_dependencies()
        create_categories()

        # create user(s)
        self.user = create_test_user(username='not_bob', password='1234')
        self.bob = create_test_user(username='bob', password='1234')

        # create data
        self.content = create_test_theory(created_by=self.user)
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
        self.opinion = create_test_opinion(content=self.content, user=self.user, dependencies=True)
        self.stats = Stats.get(self.content, Stats.TYPE.ALL)
        self.stats_dependency = self.stats.get_flat_dependency(self.fact)

    def test_create(self):
        pass

    def test_str(self):
        pass

    def test_true_statement(self):
        pass

    def test_false_statement(self):
        pass

    def test_tag_id(self):
        pass

    def test_about(self):
        pass

    def test_url(self):
        pass

    def test_is_theory(self):
        pass

    def test_is_subtheory(self):
        pass

    def test_is_evidence(self):
        pass

    def test_is_fact(self):
        pass

    def test_is_verifiable(self):
        pass

    def test_true_points(self):
        pass

    def test_false_points(self):
        pass

    def test_total_points(self):
        pass

    def test_true_percent(self):
        pass

    def test_false_percent(self):
        pass

    def test_true_ratio(self):
        pass

    def test_false_ratio(self):
        pass
