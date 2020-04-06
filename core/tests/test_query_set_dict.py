"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE.md file in the root directory of this source tree.
"""

import copy
import types

from django.test import TestCase

from core.utils import QuerySetDict


class QuerySetDictTests(TestCase):

    def setUp(self):
        self.content01 = types.SimpleNamespace()
        self.content02 = types.SimpleNamespace()
        self.opinion01 = types.SimpleNamespace()
        self.opinion02 = types.SimpleNamespace()
        self.opinion01.content = self.content01
        self.opinion02.content = self.content02
        self.content01.pk = 1
        self.content02.pk = 2

    def test_init(self):
        query_set = QuerySetDict('content.pk')
        query_set.add(self.opinion01)
        self.assertEqual(query_set.count(), 1)
        for x in query_set:
            self.assertEqual(x, self.opinion01)

    def test_get_object_key(self):
        query_set = QuerySetDict('content.pk')
        self.assertEqual(query_set.get_object_key(self.opinion01), self.content01.pk)

    def test_add_and_get(self):
        # Setup
        query_set = QuerySetDict('content.pk')
        query_set.add(self.opinion01)
        query_set.add(self.opinion02)
        self.assertEqual(query_set.get(self.content01), self.opinion01)
        self.assertEqual(query_set.get(self.content02), self.opinion02)
        self.assertEqual(query_set.get(self.content01.pk), self.opinion01)
        self.assertEqual(query_set.get(self.content02.pk), self.opinion02)
        # Adding the opinion twice will just replace it.
        query_set.add(self.opinion01)
        self.assertEqual(query_set.get(self.content01), self.opinion01)
        self.assertEqual(query_set.count(), 2)
        # Create a copy that is different.
        opinion_copy = copy.deepcopy(self.opinion01)
        opinion_copy.meh = 0  # make it different.
        # Test
        query_set.add(opinion_copy)
        self.assertEqual(query_set.get(self.content01), opinion_copy)
        self.assertNotEqual(opinion_copy, self.opinion01)
        self.assertEqual(query_set.count(), 2)

    def test_exclude(self):
        # Setup
        query_set01 = QuerySetDict('content.pk')
        query_set01.add(self.opinion01)
        query_set01.add(self.opinion02)
        self.assertEqual(query_set01.count(), 2)
        # Blah
        query_set02 = query_set01.exclude(self.content02)
        self.assertEqual(query_set01.count(), 2)
        self.assertEqual(query_set02.count(), 1)
        self.assertEqual(query_set02.get(self.content01), self.opinion01)
        self.assertIsNone(query_set02.get(self.content02))
