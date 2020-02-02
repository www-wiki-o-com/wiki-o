"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       home/tests.py
@brief      A collection of app specific unit tests
@copyright  GNU Public License, 2018
@authors    Frank Imeson
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
            'Subject here', 'Here is the message.',
            'fcimeson@wiki-o.com', ['fcimeson@gmail.com'],
            fail_silently=False,
        )
        # Test that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)

    # ******************************
    #
    # ******************************
    def test_alpha_url(self):
        response = self.client.get(reverse('home:alpha'))
        self.assertEqual(response.status_code, 200)

    # ******************************
    #
    # ******************************
    def test_about_url(self):
        response = self.client.get(reverse('home:about'))
        self.assertEqual(response.status_code, 200)

    # ******************************
    #
    # ******************************
    def test_help_url(self):
        response = self.client.get(reverse('home:help'))
        self.assertEqual(response.status_code, 200)
