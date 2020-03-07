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


# ************************************************************
#
# ************************************************************
class SimpleTest(TestCase):

    # ******************************
    #
    # ******************************
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

    # ******************************
    #
    # ******************************
    def test_alpha_url(self):
        response = self.client.get(reverse('core:alpha'))
        self.assertEqual(response.status_code, 200)

    # ******************************
    #
    # ******************************
    def test_about_url(self):
        response = self.client.get(reverse('core:about'))
        self.assertEqual(response.status_code, 200)

    # ******************************
    #
    # ******************************
    def test_help_url(self):
        response = self.client.get(reverse('core:help'))
        self.assertEqual(response.status_code, 200)
