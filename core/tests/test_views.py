"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE.md file in the root directory of this source tree.
"""

from django.test import TestCase
from django.urls import reverse


class ViewTests(TestCase):

    def test_alpha_url(self):
        response = self.client.get(reverse('core:alpha'))
        self.assertEqual(response.status_code, 200)

    def test_about_url(self):
        response = self.client.get(reverse('core:about'))
        self.assertEqual(response.status_code, 200)

    def test_help_url(self):
        response = self.client.get(reverse('core:help'))
        self.assertEqual(response.status_code, 200)
