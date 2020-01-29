# *******************************************************************************
# Wiki-O: A web service for sharing opinions and avoiding arguments.
# Copyright (C) 2018 Frank Imeson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# *******************************************************************************


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
