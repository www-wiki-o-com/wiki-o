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
from django.contrib import auth
from django.test import TestCase
from django.urls import reverse
from notifications.signals import notify

from core.utils import get_form_data, timezone_today
from theories.utils import create_categories
from users.maintence import create_test_user
from users.models import Violation, ViolationFeedback, ViolationVote

# *******************************************************************************
# Defines
# *******************************************************************************
User = auth.get_user_model()


class LogInTest(TestCase):

    def setUp(self):
        self.credentials = {
            'username': 'testuser',
            'password': '1234',
        }
        self.login = {
            'login': 'testuser',
            'password': '1234',
        }
        User.objects.create_user(**self.credentials)

    def verify_get_response(self, url, redirect_url=None, code=200):
        response = self.client.get(url)
        self.assertEqual(response.status_code, code)
        if redirect_url is not None:
            self.assertEqual(response.url.split('?')[0], redirect_url.split('?')[0])

    def verify_post_response(self,
                             url,
                             redirect_url=None,
                             post_data=None,
                             code=302,
                             verbose_level=0):
        # Get and populate form(s).
        if post_data is None:
            response = self.client.post(url)
        else:
            form_data = get_form_data(response=self.client.get(url), verbose_level=verbose_level)
            if form_data is None:
                form_data = {}
            for key in form_data:
                if key not in post_data.keys():
                    if form_data[key] is None:
                        post_data[key] = ''
                    else:
                        post_data[key] = form_data[key]
                    if verbose_level > 0:
                        print(100, key, form_data[key])
            response = self.client.post(url, post_data)
            if verbose_level > 0:
                form_data = get_form_data(response=self.client.get(url), verbose_level=10)

        # Test response.
        self.assertEqual(response.status_code, code)
        if response.status_code != 403 and redirect_url is not None:
            self.assertEqual(response.url.split('?')[0], redirect_url.split('?')[0])

        # Return
        return response

    def verify_redirect(self, response, redirect_url):
        self.assertEqual(response.url.split('?')[0], redirect_url.split('?')[0])

    def test_login(self):
        response = self.client.post('/accounts/login/', self.login, follow=True)
        self.assertTrue(response.context['user'].is_active)

    def test_post_signup(self):
        test_url = '/accounts/signup/'
        post_data = {
            'username': 'Bob',
            'email': 'bob@gmail.com',
            'password1': 'bob!!!1234BOB',
            'password2': 'bob!!!1234BOB'
        }
        response = self.verify_post_response(test_url, None, post_data, 302)
        self.assertTrue(response.context['user'].is_active)


class UserViews(TestCase):
    fixtures = ['groups.json']

    def setUp(self):
        # create user(s)
        self.bob = create_test_user(username='bob', password='1234')
        self.user = create_test_user(username='testuser', password='1234')
        self.client.login(username='testuser', password='1234')

        # setup
        create_categories()

        # notify
        notify.send(self.user, recipient=self.user, verb='Test')

    def verify_get_response(self, url, redirect_url=None, code=200):
        response = self.client.get(url)
        self.assertEqual(response.status_code, code)
        if redirect_url is not None:
            self.assertEqual(response.url.split('?')[0], redirect_url.split('?')[0])

    def verify_post_response(self,
                             url,
                             redirect_url=None,
                             post_data=None,
                             code=302,
                             verbose_level=0):
        # Get and populate form(s).
        if post_data is None:
            response = self.client.post(url)
        else:
            form_data = get_form_data(response=self.client.get(url), verbose_level=verbose_level)
            if form_data is None:
                form_data = {}
            for key in form_data:
                if key not in post_data.keys():
                    if form_data[key] is None:
                        post_data[key] = ''
                    else:
                        post_data[key] = form_data[key]
                    if verbose_level > 0:
                        print(100, key, form_data[key])
            response = self.client.post(url, post_data)
            if verbose_level > 0:
                form_data = get_form_data(response=self.client.get(url), verbose_level=10)

        # Test response
        self.assertEqual(response.status_code, code)
        if response.status_code != 403 and redirect_url is not None:
            self.assertEqual(response.url.split('?')[0], redirect_url.split('?')[0])

        # Return
        return response

    def verify_redirect(self, response, redirect_url):
        self.assertEqual(response.url.split('?')[0], redirect_url.split('?')[0])

    def test_login(self):
        user = auth.get_user(self.client)
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user, self.user)

    def test_get_profile(self):
        test_url = reverse('users:profile-edit')
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)

    def test_get_notifications(self):
        test_url = reverse('users:notifications')
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)

    def test_get_self_detail(self):
        test_url = reverse('users:profile-detail', kwargs={'pk': self.user.pk})
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)

    def test_get_bobs_detail(self):
        test_url = reverse('users:profile-detail', kwargs={'pk': self.bob.pk})
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)

    def test_post_profile(self):
        test_url = reverse('users:profile-edit')
        post_data = {
            'username': 'Bobarinio',
            'fullname_visible': True,
            'birth_date': timezone_today()
        }
        self.verify_post_response(test_url, None, post_data, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'Bobarinio')

    def test_post_notifications(self):
        self.assertEqual(self.user.notifications.count(), 1)
        test_url = reverse('users:notifications')
        post_data = {'action': 'Delete', 'notifications-0-select': True}
        self.verify_post_response(test_url, None, post_data, 302)
        self.assertEqual(self.user.notifications.count(), 0)


class UserViolations(TestCase):

    def test_vote_choices(self):
        """Test that ViolationVote.VOTE_OUTCOMES is consistent with Violation.STATUS"""

        # Ensure all choices are accounted for.
        self.assertEqual(len(ViolationVote.VOTE_OUTCOMES), 3)
        self.assertEqual(len(ViolationVote.VOTE_OUTCOMES), len(Violation.STATUS_CLOSED))
        self.assertEqual(len(ViolationVote.VOTE_CHOICES), len(ViolationVote.VOTE_OUTCOMES) + 1)

        # Test that the no vote is mapped to 0.
        self.assertEqual(ViolationVote.VOTE_CHOICES.NO_VOTE, 0)

        # Test that VOTE_CHOICES and VOTE_OUTCOMES is consistent.
        self.assertEqual(ViolationVote.VOTE_CHOICES.IGNORE, ViolationVote.VOTE_OUTCOMES.IGNORE)
        self.assertEqual(ViolationVote.VOTE_CHOICES.WARN, ViolationVote.VOTE_OUTCOMES.WARN)
        self.assertEqual(ViolationVote.VOTE_CHOICES.STRIKE, ViolationVote.VOTE_OUTCOMES.STRIKE)

        # Test that ViolationVote.VOTE_CHOICES and Violation.STATUS is consistent.
        self.assertEqual(ViolationVote.VOTE_CHOICES.IGNORE, Violation.STATUS.IGNORED)
        self.assertEqual(ViolationVote.VOTE_CHOICES.WARN, Violation.STATUS.WARNING)
        self.assertEqual(ViolationVote.VOTE_CHOICES.STRIKE, Violation.STATUS.STRIKE)

    def test_feedback_choices(self):
        """Test that ViolationFeedback.ACTION_FEEDBACK is consistent with Violation.STATUS"""

        # Ensure all choices are accounted for.
        self.assertEqual(len(ViolationFeedback.ACTION_FEEDBACK), 7)
        self.assertEqual(len(ViolationFeedback.ACTION_FEEDBACK), len(Violation.STATUS) + 1)
        self.assertEqual(len(ViolationFeedback.ACTION_FEEDBACK),
                         len(ViolationFeedback.OPEN_ACTION_CHOICES) + 2)
        self.assertEqual(len(ViolationFeedback.ACTION_FEEDBACK),
                         len(ViolationFeedback.CLOSED_ACTION_CHOICES) + 2)

        # Test that the no action is mapped to 0.
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.NO_ACTION, 0)
        self.assertEqual(ViolationFeedback.OPEN_ACTION_CHOICES.NO_ACTION, 0)
        self.assertEqual(ViolationFeedback.CLOSED_ACTION_CHOICES.NO_ACTION, 0)

        # Test that ACTION_FEEDBACK and OPEN_ACTION_CHOICES is consistent.
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.NO_ACTION,
                         ViolationFeedback.OPEN_ACTION_CHOICES.NO_ACTION)
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.CLOSED_POLL,
                         ViolationFeedback.OPEN_ACTION_CHOICES.CLOSE_POLL)
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.IGNORED,
                         ViolationFeedback.OPEN_ACTION_CHOICES.IGNORE)
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.WARNING,
                         ViolationFeedback.OPEN_ACTION_CHOICES.WARN)
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.STRIKE,
                         ViolationFeedback.OPEN_ACTION_CHOICES.STRIKE)

        # Test that ACTION_FEEDBACK and CLOSED_ACTION_CHOICES is consistent.
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.NO_ACTION,
                         ViolationFeedback.CLOSED_ACTION_CHOICES.NO_ACTION)
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.OPENED_POLL,
                         ViolationFeedback.CLOSED_ACTION_CHOICES.OPEN_POLL)
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.IGNORED,
                         ViolationFeedback.CLOSED_ACTION_CHOICES.IGNORE)
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.WARNING,
                         ViolationFeedback.CLOSED_ACTION_CHOICES.WARN)
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.STRIKE,
                         ViolationFeedback.CLOSED_ACTION_CHOICES.STRIKE)

        # Test that ViolationFeedback.ACTION_FEEDBACK and Violation.STATUS is consistent.
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.REPORTED, Violation.STATUS.REPORTED)
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.OPENED_POLL, Violation.STATUS.POLLING)
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.CLOSED_POLL, Violation.STATUS.PENDING)
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.IGNORED, Violation.STATUS.IGNORED)
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.WARNING, Violation.STATUS.WARNING)
        self.assertEqual(ViolationFeedback.ACTION_FEEDBACK.STRIKE, Violation.STATUS.STRIKE)
