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
from django.core import mail


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
