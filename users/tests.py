"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       users/tests.py
@brief      A collection of app specific unit tests
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# Imports
# *******************************************************************************
import datetime

from django.test import TestCase
from django.urls import reverse
from django.contrib import auth
from notifications.signals import notify

from theories.utils import *
from users.maintence import create_test_user
from core.utils import get_form_data


# *******************************************************************************
# Defines
# *******************************************************************************
User = auth.get_user_model()


# *******************************************************************************
#
#
#
#
#
#
#
#
# *******************************************************************************
class LogInTest(TestCase):

    # ******************************
    #
    # ******************************
    def setUp(self):
        self.credentials = {
            'username': 'testuser',
            'password': '1234',
        }
        self.login = {
            'login':    'testuser',
            'password': '1234',
        }
        User.objects.create_user(**self.credentials)

    # ******************************
    # Verify GET
    # ******************************

    def verify_get_response(self, url, redirect_url=None, code=200):
        response = self.client.get(url)
        self.assertEqual(response.status_code, code)
        if redirect_url is not None:
            self.assertTrue(url_match(response.url, redirect_url))

    # ******************************
    # Verify POST - ViewsTestBase
    # ******************************
    def verify_post_response(self, url, redirect_url=None, post_data=None, code=302, verbose_level=0):
        # get and populate form(s)
        if post_data is None:
            response = self.client.post(url)
        else:
            form_data = get_form_data(response=self.client.get(
                url), verbose_level=verbose_level)
            if form_data is None:
                form_data = {}
            for key in form_data.keys():
                if key not in post_data.keys():
                    if form_data[key] is None:
                        post_data[key] = ''
                    else:
                        post_data[key] = form_data[key]
                    if verbose_level > 0:
                        print(100, key, form_data[key])
            response = self.client.post(url, post_data)
            if verbose_level > 0:
                form_data = get_form_data(
                    response=self.client.get(url), verbose_level=10)

        # test response
        self.assertEqual(response.status_code, code)
        if response.status_code != 403 and redirect_url is not None:
            self.assertEqual(response.url.split(
                '?')[0], redirect_url.split('?')[0])

        # return
        return response

    # ******************************
    # Verify Redirect - ViewsTestBase
    # ******************************
    def verify_redirect(self, response, redirect_url):
        self.assertEqual(response.url.split(
            '?')[0], redirect_url.split('?')[0])

    # ******************************
    #
    # ******************************
    def test_login(self):
        response = self.client.post(
            '/accounts/login/', self.login, follow=True)
        self.assertTrue(response.context['user'].is_active)

    # ******************************
    #
    # ******************************
    def test_post_signup(self):
        test_url = '/accounts/signup/'
        post_data = {'username': 'Bob', 'email': 'bob@gmail.com',
                     'password1': 'bob!!!1234BOB', 'password2': 'bob!!!1234BOB'}
        response = self.verify_post_response(test_url, None, post_data, 302)
        self.assertTrue(response.context['user'].is_active)


# ************************************************************
#
#
#
#
#
#
# ************************************************************
class UserViews(TestCase):
    fixtures = ['groups.json']

    # ******************************
    # Setup
    # ******************************
    def setUp(self):
        # create user(s)
        self.bob = create_test_user(username='bob', password='1234')
        self.user = create_test_user(username='testuser', password='1234')
        self.client.login(username='testuser', password='1234')

        # setup
        create_reserved_nodes()
        create_categories()

        # notify
        notify.send(self.user, recipient=self.user, verb='Test')

    # ******************************
    # Verify GET
    # ******************************
    def verify_get_response(self, url, redirect_url=None, code=200):
        response = self.client.get(url)
        self.assertEqual(response.status_code, code)
        if redirect_url is not None:
            self.assertTrue(url_match(response.url, redirect_url))

    # ******************************
    # Verify POST - ViewsTestBase
    # ******************************
    def verify_post_response(self, url, redirect_url=None, post_data=None, code=302, verbose_level=0):
        # get and populate form(s)
        if post_data is None:
            response = self.client.post(url)
        else:
            form_data = get_form_data(response=self.client.get(
                url), verbose_level=verbose_level)
            if form_data is None:
                form_data = {}
            for key in form_data.keys():
                if key not in post_data.keys():
                    if form_data[key] is None:
                        post_data[key] = ''
                    else:
                        post_data[key] = form_data[key]
                    if verbose_level > 0:
                        print(100, key, form_data[key])
            response = self.client.post(url, post_data)
            if verbose_level > 0:
                form_data = get_form_data(
                    response=self.client.get(url), verbose_level=10)

        # test response
        self.assertEqual(response.status_code, code)
        if response.status_code != 403 and redirect_url is not None:
            self.assertEqual(response.url.split(
                '?')[0], redirect_url.split('?')[0])

        # return
        return response

    # ******************************
    # Verify Redirect - ViewsTestBase
    # ******************************
    def verify_redirect(self, response, redirect_url):
        self.assertEqual(response.url.split(
            '?')[0], redirect_url.split('?')[0])

    # ******************************
    # Login
    # ******************************
    def test_login(self):
        user = auth.get_user(self.client)
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user, self.user)

    # ******************************
    #
    # ******************************
    def test_get_profile(self):
        test_url = reverse('users:profile-edit')
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)

    # ******************************
    #
    # ******************************
    def test_get_notifications(self):
        test_url = reverse('users:notifications')
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)

    # ******************************
    #
    # ******************************
    def test_get_self_detail(self):
        test_url = reverse('users:profile-detail', kwargs={'pk': self.user.pk})
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)

    # ******************************
    #
    # ******************************
    def test_get_bobs_detail(self):
        test_url = reverse('users:profile-detail', kwargs={'pk': self.bob.pk})
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)

    # ******************************
    #
    # ******************************
    def test_post_profile(self):
        test_url = reverse('users:profile-edit')
        post_data = {'username': 'Bobarinio', 'fullname_visible': True,
                     'birth_date': datetime.date.today()}
        self.verify_post_response(test_url, None, post_data, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'Bobarinio')

    # ******************************
    #
    # ******************************
    def test_post_notifications(self):
        self.assertEqual(self.user.notifications.count(), 1)
        test_url = reverse('users:notifications')
        post_data = {'action': 'Delete', 'notifications-0-select': True}
        self.verify_post_response(test_url, None, post_data, 302)
        self.assertEqual(self.user.notifications.count(), 0)
