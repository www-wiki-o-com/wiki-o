"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       forum/tests.py
@brief      A collection of app specific unit tests
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# imports
# *******************************************************************************
from django.test import TestCase
from django.urls import reverse
from users.utils import *
from core.utils import *


# ************************************************************
# Base test class for views
# ToDo:
#   Test view post
#   Test post (allowed)
#   Test post (not allowed)
#   Test?
#
#
# ************************************************************
class ViewsTestBase():

    # ******************************
    # Setup - ViewsTestBase
    # ******************************
    def create_data(self, user=None, created_by=None):
        pass

    # ******************************
    # Verify GET - ViewsTestBase
    # ******************************
    def verify_get_response(self, url, redirect_url=None, code=200):
        response = self.client.get(url)
        self.assertEqual(response.status_code, code)
        if redirect_url is not None:
            self.assertEqual(response.url.split(
                '?')[0], redirect_url.split('?')[0])

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
    # GET - ViewsTestBase
    # ******************************
    def test_get_index(self, override=False):
        test_url = reverse('forum:index')
        self.verify_get_response(test_url, code=200)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # GET - ViewsTestBase
    # ******************************
    def test_get_forum01(self, forum='announcements-1', override=False, redirect_url=None, code=200):
        test_url = '/feedback/forum/%s/' % forum
        self.verify_get_response(
            test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)


# ************************************************************
# AnonymousUser
#
#
#
#
#
# ************************************************************
class AnonymousUserViews(TestCase, ViewsTestBase):
    fixtures = ['groups.json', 'users.json', 'forums.json']

    # ******************************
    # Setup - AnonymousUser
    # ******************************
    def setUp(self):
        super().create_data()

    # ******************************
    # GET - AnonymousUser
    # ******************************
    def test_get_index(self):
        super().test_get_index(
            override=True,
        )

    # ******************************
    # GET - AnonymousUser
    # ******************************
    def test_get_forum01(self):
        super().test_get_forum01(
            override=True,
            code=302,
            redirect_url='/accounts/login/',
            forum='announcements-1',
        )

    # ******************************
    # GET - AnonymousUser
    # ******************************
    def test_get_forum02(self):
        super().test_get_forum01(
            override=True,
            code=302,
            redirect_url='/accounts/login/',
            forum='suggestions-2',
        )

    # ******************************
    # GET - AnonymousUser
    # ******************************
    def test_get_forum03(self):
        super().test_get_forum01(
            override=True,
            code=302,
            redirect_url='/accounts/login/',
            forum='criticisms-and-testimonials-3',
        )

    # ******************************
    # GET - AnonymousUser
    # ******************************
    def test_get_forum04(self):
        super().test_get_forum01(
            override=True,
            code=302,
            redirect_url='/accounts/login/',
            forum='bugs-4',
        )


# ************************************************************
# Level00UserViews
#
#
#
#
#
# ************************************************************
class Level00UserViews(TestCase, ViewsTestBase):
    fixtures = ['groups.json', 'users.json', 'forums.json']

    # ******************************
    # Setup - Level00UserViews
    # ******************************
    def setUp(self):
        super().create_data()
        self.user = create_test_user(
            username='testuser', password='1234', level=0)
        self.client.login(username='testuser', password='1234')

    # ******************************
    # GET - Level00UserViews
    # ******************************
    def test_get_index(self):
        super().test_get_index(
            override=True,
        )

    # ******************************
    # GET - Level00UserViews
    # ******************************
    def test_get_forum01(self):
        super().test_get_forum01(
            override=True,
            forum='announcements-1',
        )

    # ******************************
    # GET - Level00UserViews
    # ******************************
    def test_get_forum02(self):
        super().test_get_forum01(
            override=True,
            forum='suggestions-2',
        )

    # ******************************
    # GET - Level00UserViews
    # ******************************
    def test_get_forum03(self):
        super().test_get_forum01(
            override=True,
            forum='criticisms-and-testimonials-3',
        )

    # ******************************
    # GET - Level00UserViews
    # ******************************
    def test_get_forum04(self):
        super().test_get_forum01(
            override=True,
            forum='bugs-4',
        )
