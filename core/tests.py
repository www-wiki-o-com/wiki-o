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
from django.core import mail

from core.utils import Choices


class SystemTests(TestCase):

    def test_send_email(self):
        # Send message.
        mail.send_mail(
            'Subject here',
            'Here is the message.',
            'fcimeson@wiki-o.com',
            ['fcimeson@gmail.com'],
            fail_silently=False,
        )
        # Test that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)


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


class ChoicesTests(TestCase):

    def test_create(self):
        Choices(
            "TEST00",
            "TEST01",
        )

        Choices(
            (0, "TEST00"),
            (1, "TEST01"),
        )

        Choices(
            (0, "TEST00", ("Blah")),
            (1, "TEST01", ("Blah")),
        )

    def test_addition01(self):
        x = Choices(
            (0, "TEST00", ("Blah")),
            (1, "TEST01", ("Blah")),
        )

        y = Choices(
            (0, "TEST00", ("Blah")),
            (2, "TEST02", ("Blah")),
        )

        self.assertEqual(len(x + y), 3)
        self.assertEqual(len(y + x), 3)

    def test_addition02(self):
        x = Choices(
            (0, "TEST00", ("Blah")),
            (1, "TEST01", ("Blah")),
            unique=False,
        )

        y = Choices(
            (0, "TEST00", ("Blah")),
            (2, "TEST02", ("Blah")),
            unique=False,
        )

        self.assertEqual(len(x + y), 4)
        self.assertEqual(len(y + x), 4)
