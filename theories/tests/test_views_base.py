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
import random

from django.contrib import auth
from django.shortcuts import get_object_or_404, redirect, render
from django.test import TestCase
from django.urls import reverse

from core.utils import get_form_data, get_or_none
from theories.converters import CONTENT_PK_CYPHER
from theories.model_utils import convert_content_type
from theories.models.content import Content
from theories.models.opinions import Opinion, OpinionDependency
from theories.tests.utils import (create_test_evidence, create_test_opinion, create_test_subtheory,
                                  create_test_theory)
from theories.utils import create_categories, create_reserved_dependencies
from users.maintence import create_test_user

# *******************************************************************************
# Defines
# *******************************************************************************
User = auth.get_user_model()

# *******************************************************************************
# Classes
# *******************************************************************************


# ************************************************************
# Base test class for views
# ToDo:
#   - test swap titles
#   - test path
#   - test links?
#
#
#
#
#
# ************************************************************
class ViewsTestBase():

    # ******************************
    # Setup - ViewsTestBase
    # ******************************
    def create_data(self, user=None, created_by=None):
        # setup
        create_reserved_dependencies()
        create_categories()
        random.seed(0)
        Content.update_intuition()

        # create user(s)
        self.bob = create_test_user(username='bob', password='1234')
        if user is None:
            user = self.bob
        if created_by is None:
            created_by = self.bob

        # theory
        self.content = create_test_theory(created_by=created_by, backup=True)
        self.subtheory = create_test_subtheory(parent_theory=self.content, created_by=created_by)
        self.evidence = create_test_evidence(parent_theory=self.subtheory,
                                             created_by=created_by,
                                             backup=True)
        self.fact = create_test_evidence(parent_theory=self.content,
                                         title='Fact',
                                         fact=True,
                                         created_by=created_by)
        self.fiction = create_test_evidence(parent_theory=self.content,
                                            title='Fiction',
                                            fact=False,
                                            created_by=created_by)

        # opinions
        self.bobs_opinion = create_test_opinion(content=self.content, user=self.bob)
        if user != self.bob:
            self.my_opinion = create_test_opinion(content=self.content, user=user)
        else:
            self.my_opinion = self.bobs_opinion

    # ******************************
    # Verify GET - ViewsTestBase
    # ******************************
    def verify_get_response(self, url, redirect_url=None, code=200):
        response = self.client.get(url)
        self.assertEqual(response.status_code, code)
        if redirect_url is not None:
            self.assertEqual(response.url.split('?')[0], redirect_url.split('?')[0])

    # ******************************
    # Verify POST - ViewsTestBase
    # ******************************
    def verify_post_response(self,
                             url,
                             redirect_url=None,
                             post_data=None,
                             code=302,
                             verbose_level=0):
        # get and populate form(s)
        if post_data is None:
            response = self.client.post(url)
        else:
            form_data = get_form_data(response=self.client.get(url), verbose_level=verbose_level)
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
                form_data = get_form_data(response=self.client.get(url), verbose_level=10)

        # test response
        self.assertEqual(response.status_code, code)
        if response.status_code != 403 and redirect_url is not None:
            self.assertEqual(response.url.split('?')[0], redirect_url.split('?')[0])

        # return
        return response

    # ******************************
    # Verify Redirect - ViewsTestBase
    # ******************************
    def verify_redirect(self, response, redirect_url):
        self.assertEqual(response.url.split('?')[0], redirect_url.split('?')[0])

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_index(self, override=False):
        test_url = reverse('theories:index')
        self.verify_get_response(test_url, code=200)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_index_category(self, override=False, category='all'):
        test_url = reverse('theories:theories', kwargs={'category_slug': category})
        self.verify_get_response(test_url, code=200)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_activity(self, override=False):
        test_url = reverse('theories:activity', kwargs={'category_slug': 'all'})
        self.verify_get_response(test_url, code=200)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_theory_create(self, override=False, redirect_url=None, code=200):
        test_url = reverse('theories:theory-create', kwargs={'category_slug': 'all'})
        self.verify_get_response(test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_theory_detail(self, override=False):
        test_url = reverse('theories:theory-detail', kwargs={'content_pk': self.content.pk})
        self.verify_get_response(test_url, code=200)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_theory_edit(self, override=False, redirect_url=None, code=200):
        test_url = reverse('theories:theory-edit', kwargs={'content_pk': self.content.pk})
        self.verify_get_response(test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_theory_merge(self, override=False, redirect_url=None, code=200):
        test_url = reverse('theories:theory-merge', kwargs={'content_pk': self.content.pk})
        self.verify_get_response(test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_theory_backup(self, override=False, redirect_url=None, code=200):
        test_url = reverse('theories:theory-backup', kwargs={'content_pk': self.content.pk})
        self.verify_get_response(test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_theory_restore(self, override=False, redirect_url=None, code=200):
        test_url = reverse('theories:theory-restore', kwargs={'content_pk': self.content.pk})
        self.verify_get_response(test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_theory_activity(self, override=False, redirect_url=None, code=200):
        test_url = reverse('theories:theory-activity', kwargs={'content_pk': self.content.pk})
        self.verify_get_response(test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_theory_edit_evidence(self, override=False, redirect_url=None, code=200):
        test_url = reverse('theories:theory-edit-evidence', kwargs={'content_pk': self.content.pk})
        self.verify_get_response(test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_theory_edit_subtheories(self, override=False, redirect_url=None, code=200):
        test_url = reverse('theories:theory-edit-subtheories',
                           kwargs={'content_pk': self.content.pk})
        self.verify_get_response(test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_theory_inherit(self, override=False, redirect_url=None, code=200):
        test_url = reverse('theories:theory-inherit',
                           kwargs={
                               'pk02': self.content.pk,
                               'pk01': self.subtheory.pk
                           })
        self.verify_get_response(test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_evidence_detail(self, override=False):
        test_url = reverse('theories:evidence-detail', kwargs={'content_pk': self.evidence.pk})
        self.verify_get_response(test_url, code=200)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_evidence_edit(self, override=False, redirect_url=None, code=200):
        test_url = reverse('theories:evidence-edit', kwargs={'content_pk': self.evidence.pk})
        self.verify_get_response(test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_evidence_merge(self, override=False, redirect_url=None, code=200):
        test_url = reverse('theories:evidence-merge', kwargs={'content_pk':
            self.evidence.pk}) + '?path=%s' % CONTENT_PK_CYPHER.to_url(self.subtheory.pk)
        self.verify_get_response(test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_evidence_restore(self, override=False, redirect_url=None, code=200):
        test_url = reverse('theories:evidence-restore', kwargs={'content_pk': self.evidence.pk})
        self.verify_get_response(test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_evidence_activity(self, override=False, redirect_url=None, code=200):
        test_url = reverse('theories:evidence-activity', kwargs={'content_pk': self.evidence.pk})
        self.verify_get_response(test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_opinion_demo(self, override=False):
        test_url = reverse('theories:opinion-analysis',
                           kwargs={
                               'content_pk': 0,
                               'opinion_slug': 'debug'
                           })
        self.verify_get_response(test_url, code=200)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_opinion_detail(self, override=False):
        test_url = reverse('theories:theory-detail',
                           kwargs={
                               'content_pk': self.bobs_opinion.content.pk,
                               'opinion_pk': self.bobs_opinion.pk
                           })
        self.verify_get_response(test_url, code=200)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_my_opinion(self, override=False, redirect_url=None, code=302):
        test_url = reverse('theories:get_my_opinion', kwargs={'content_pk': self.content.pk})
        self.verify_get_response(test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_opinion_edit(self, override=False, redirect_url=None, code=200):
        test_url = reverse('theories:opinion-edit', kwargs={'content_pk': self.content.pk})
        self.verify_get_response(test_url, redirect_url=redirect_url, code=code)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_opinion_slug(self, override=False):
        test_url = reverse('theories:theory-detail',
                           kwargs={
                               'content_pk': self.content.pk,
                               'opinion_slug': 'all'
                           })
        self.verify_get_response(test_url, code=200)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_user_vs_user(self, override=False):
        test_url = reverse('theories:opinion-compare',
                           kwargs={
                               'content_pk': self.bobs_opinion.content.pk,
                               'opinion_pk01': self.bobs_opinion.pk,
                               'opinion_pk02': self.bobs_opinion.pk
                           })
        self.verify_get_response(test_url, code=200)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_user_vs_slug(self, override=False):
        test_url = reverse('theories:opinion-compare',
                           kwargs={
                               'content_pk': self.bobs_opinion.content.pk,
                               'opinion_pk01': self.bobs_opinion.pk,
                               'opinion_slug02': 'all'
                           })
        self.verify_get_response(test_url, code=200)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_slug_vs_user(self, override=False):
        test_url = reverse('theories:opinion-compare',
                           kwargs={
                               'content_pk': self.bobs_opinion.content.pk,
                               'opinion_slug01': 'all',
                               'opinion_pk02': self.bobs_opinion.pk
                           })
        self.verify_get_response(test_url, code=200)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Get - ViewsTestBase
    # ******************************
    def test_get_slug_vs_slug(self, override=False):
        test_url = reverse('theories:opinion-compare',
                           kwargs={
                               'content_pk': self.content.pk,
                               'opinion_slug01': 'all',
                               'opinion_slug02': 'all'
                           })
        self.verify_get_response(test_url, code=200)
        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # test categories
    # test activity
    # test notifications
    # ******************************
    def test_post_theory_create(self, override=False, redirect_url=None, code=302, created=True):
        # test response
        test_url = reverse('theories:theory-create', kwargs={'category_slug': 'all'})
        post_data = {'title01': 'New Title'}
        response = self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change
        new_theory = get_or_none(Content.objects.all(), title01='New Title')
        if created:
            # test change
            self.assertIsNotNone(new_theory)

            # test redirect
            redirect_url = reverse('theories:theory-detail', kwargs={'content_pk': new_theory.pk})
            self.verify_redirect(response, redirect_url)
        else:
            # test changed did not occure
            self.assertIsNone(new_theory)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************

    def test_post_theory_edit(self, override=False, redirect_url=None, code=302, modified=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:theory-detail', kwargs={'content_pk': self.content.pk})

        # test response
        test_url = reverse('theories:theory-edit', kwargs={'content_pk': self.content.pk})
        post_data = {'title01': 'Edited Title'}
        self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change
        self.content.refresh_from_db()
        if modified:
            self.assertEqual(self.content.title01, 'Edited Title')
        else:
            self.assertNotEqual(self.content.title01, 'Edited Title')

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_theory_merge(self, override=False, redirect_url=None, code=302, modified=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:theory-detail', kwargs={'content_pk': self.content.pk})

        # test response
        test_url = reverse('theories:theory-merge', kwargs={'content_pk': self.content.pk})
        post_data = {'form-0-select': True}
        self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change
        if modified:
            self.assertNotIn(self.subtheory, self.content.get_dependencies())
        else:
            self.assertIn(self.subtheory, self.content.get_dependencies())

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_theory_backup(self, override=False, redirect_url=None, code=302, modified=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:theory-detail', kwargs={'content_pk': self.content.pk})
        old_date = self.content.get_revisions().first().revision.date_created

        # test response
        test_url = reverse('theories:theory-backup', kwargs={'content_pk': self.content.pk})
        post_data = {'form-0-select': True}
        self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change
        new_date = self.content.get_revisions().first().revision.date_created
        if modified:
            self.assertNotEqual(old_date, new_date)
        else:
            self.assertEqual(old_date, new_date)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_theory_delete_backup(self,
                                       override=False,
                                       redirect_url=None,
                                       code=302,
                                       modified=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:theory-detail', kwargs={'content_pk': self.content.pk})

        # test response
        test_url = reverse('theories:theory-restore', kwargs={'content_pk': self.content.pk})
        post_data = {'form-0-delete': True}
        self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change
        if modified:
            self.assertEqual(self.content.get_revisions().count(), 0)
        else:
            self.assertEqual(self.content.get_revisions().count(), 1)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_theory_edit_evidence(self,
                                       override=False,
                                       redirect_url=None,
                                       code=302,
                                       modified=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:theory-detail',
                                   kwargs={'content_pk': self.subtheory.pk})

        # test response
        test_url = reverse('theories:theory-edit-evidence',
                           kwargs={'content_pk': self.subtheory.pk})
        post_data = {'form-0-title01': 'Edited Title'}
        self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change
        self.evidence.refresh_from_db()
        if modified:
            self.assertEqual(self.evidence.title01, 'Edited Title')
        else:
            self.assertNotEqual(self.evidence.title01, 'Edited Title')

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_theory_edit_subtheories(self,
                                          override=False,
                                          redirect_url=None,
                                          code=302,
                                          modified=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:theory-detail', kwargs={'content_pk': self.content.pk})

        # test response
        test_url = reverse('theories:theory-edit-subtheories',
                           kwargs={'content_pk': self.content.pk})
        post_data = {'form-0-title01': 'Edited Title'}
        self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change
        self.subtheory.refresh_from_db()
        if modified:
            self.assertEqual(self.subtheory.title01, 'Edited Title')
        else:
            self.assertNotEqual(self.subtheory.title01, 'Edited Title')

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_theory_new_evidence(self,
                                      override=False,
                                      redirect_url=None,
                                      code=302,
                                      created=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:theory-detail',
                                   kwargs={'content_pk': self.subtheory.pk})

        # test response
        test_url = reverse('theories:theory-edit-evidence',
                           kwargs={'content_pk': self.subtheory.pk})
        post_data = {'form-1-title01': 'New Title'}
        response = self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change
        evidence = get_or_none(Content.objects.all(), title01='New Title')
        if created:
            self.assertIsNotNone(evidence)
        else:
            self.assertIsNone(evidence)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_theory_new_subtheories(self,
                                         override=False,
                                         redirect_url=None,
                                         code=302,
                                         created=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:theory-detail', kwargs={'content_pk': self.content.pk})

        # test response
        test_url = reverse('theories:theory-edit-subtheories',
                           kwargs={'content_pk': self.content.pk})
        post_data = {'form-1-title01': 'New Title'}
        response = self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change
        subtheory = get_or_none(Content.objects.all(), title01='New Title')
        if created:
            self.assertIsNotNone(subtheory)
        else:
            self.assertIsNone(subtheory)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_theory_inherit(self, override=False, redirect_url=None, code=302, modified=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:theory-detail', kwargs={'content_pk': self.content.pk})

        # test response
        test_url = reverse('theories:theory-inherit',
                           kwargs={
                               'pk02': self.content.pk,
                               'pk01': self.content.pk
                           })
        post_data = {'form-0-select': True}
        self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change
        if modified:
            self.assertIn(self.evidence, self.content.get_dependencies())
        else:
            self.assertNotIn(self.evidence, self.content.get_dependencies())

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_theory_delete(self, override=False, redirect_url=None, code=302, deleted=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:index')

        # test response
        test_url = reverse('theories:theory-delete', kwargs={'content_pk': self.content.pk})
        self.verify_post_response(test_url, redirect_url, None, code)

        # test change
        self.content.refresh_from_db()
        if deleted:
            self.assertTrue(self.content.is_deleted())
        else:
            self.assertFalse(self.content.is_deleted())

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_theory_convert01(self,
                                   override=False,
                                   redirect_url=None,
                                   code=302,
                                   modified=True):
        # test response
        test_url = reverse('theories:theory-convert', kwargs={'content_pk':
            self.subtheory.pk}) + '?path=%s' % CONTENT_PK_CYPHER.to_url(self.content.pk)
        post_data = {'verifiable': True}
        self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change
        self.subtheory.refresh_from_db()
        if modified:
            self.assertEqual(self.subtheory.content_type, Content.TYPE.FACT)
        else:
            self.assertEqual(self.subtheory.content_type, Content.TYPE.THEORY)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_theory_convert02(self,
                                   override=False,
                                   redirect_url=None,
                                   code=302,
                                   modified=True):
        # test response
        test_url = reverse('theories:theory-convert', kwargs={'content_pk':
            self.subtheory.pk}) + '?path=%s' % CONTENT_PK_CYPHER.to_url(self.content.pk)
        post_data = {'verifiable': False}
        self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change
        self.subtheory.refresh_from_db()
        if modified:
            self.assertEqual(self.subtheory.content_type, Content.TYPE.EVIDENCE)
        else:
            self.assertEqual(self.subtheory.content_type, Content.TYPE.THEORY)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_theory_revert(self, override=False, redirect_url=None, code=302, modified=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:theory-detail', kwargs={'content_pk': self.content.pk})
        self.content.title01 = 'Changed'
        self.content.save()

        # test response
        version = self.content.get_revisions().first()
        test_url = reverse('theories:theory-revert',
                           kwargs={
                               'content_pk': self.content.pk,
                               'version_id': version.pk
                           })
        self.verify_post_response(test_url, redirect_url, None, code)

        # test change
        self.content.refresh_from_db()
        if modified:
            self.assertEqual(self.content.title01, 'Theory')
        else:
            self.assertEqual(self.content.title01, 'Changed')

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_evidence_edit(self, override=False, redirect_url=None, code=302, modified=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:evidence-detail',
                                   kwargs={'content_pk': self.evidence.pk})

        # test response
        test_url = reverse('theories:evidence-edit', kwargs={'content_pk': self.evidence.pk})
        post_data = {'title01': 'Edited Title'}
        self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change occurred
        self.evidence.refresh_from_db()
        if modified:
            self.assertEqual(self.evidence.title01, 'Edited Title')
        else:
            self.assertNotEqual(self.evidence.title01, 'Edited Title')

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_evidence_merge(self, override=False, redirect_url=None, code=302, modified=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:evidence-detail',
                                   kwargs={'content_pk': self.fiction.pk})

        # test response
        test_url = reverse('theories:evidence-merge', kwargs={'content_pk':
            self.fiction.pk}) + '?path=%s' % CONTENT_PK_CYPHER.to_url(self.content.pk)
        post_data = {'form-0-select': True}
        self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change
        if modified:
            self.assertNotIn(self.evidence, self.subtheory.get_dependencies())
            self.assertIn(self.fiction, self.subtheory.get_dependencies())
        else:
            self.assertIn(self.evidence, self.subtheory.get_dependencies())
            self.assertNotIn(self.fiction, self.subtheory.get_dependencies())

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_evidence_delete_backup(self,
                                         override=False,
                                         redirect_url=None,
                                         code=302,
                                         modified=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:evidence-detail',
                                   kwargs={'content_pk': self.evidence.pk})

        # test response
        test_url = reverse('theories:evidence-restore', kwargs={'content_pk': self.evidence.pk})
        post_data = {'form-0-delete': True}
        self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change
        if modified:
            self.assertEqual(self.evidence.get_revisions().count(), 0)
        else:
            self.assertEqual(self.evidence.get_revisions().count(), 1)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_evidence_delete(self, override=False, redirect_url=None, code=302, deleted=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:theory-detail',
                                   kwargs={'content_pk': self.subtheory.pk})

        # test response
        test_url = reverse('theories:evidence-delete', kwargs={'content_pk':
            self.evidence.pk}) + '?path=%s' % CONTENT_PK_CYPHER.to_url(self.subtheory.pk)
        self.verify_post_response(test_url, redirect_url, None, code)

        # test change occured
        self.evidence.refresh_from_db()
        if deleted:
            self.assertTrue(self.evidence.is_deleted())
        else:
            self.assertFalse(self.evidence.is_deleted())

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_evidence_backup(self, override=False, redirect_url=None, code=302, modified=True):
        # setup
        old_date = self.evidence.get_revisions().first().revision.date_created

        # test response
        test_url = reverse('theories:evidence-backup', kwargs={'content_pk': self.evidence.pk})
        self.verify_post_response(test_url, redirect_url, None, code)

        # test change
        new_date = self.evidence.get_revisions().first().revision.date_created
        if modified:
            self.assertNotEqual(old_date, new_date)
        else:
            self.assertEqual(old_date, new_date)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_evidence_convert(self,
                                   override=False,
                                   redirect_url=None,
                                   code=302,
                                   modified=True):
        # test response
        test_url = reverse('theories:evidence-convert', kwargs={'content_pk':
            self.evidence.pk}) + '?path=%s' % CONTENT_PK_CYPHER.to_url(self.subtheory.pk)
        self.verify_post_response(test_url, redirect_url, None, code)

        # test change
        self.evidence.refresh_from_db()
        if modified:
            self.assertEqual(self.evidence.content_type, Content.TYPE.THEORY)
        else:
            self.assertEqual(self.evidence.content_type, Content.TYPE.EVIDENCE)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_evidence_revert(self, override=False, redirect_url=None, code=302, modified=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:evidence-detail',
                                   kwargs={'content_pk': self.evidence.pk})
        self.evidence.title01 = 'Changed'
        self.evidence.save()

        # test response
        version = self.evidence.get_revisions().first()
        test_url = reverse('theories:evidence-revert',
                           kwargs={
                               'content_pk': self.evidence.pk,
                               'version_id': version.pk
                           }) + '?path=%s' % CONTENT_PK_CYPHER.to_url(self.subtheory.pk)
        self.verify_post_response(test_url, redirect_url, None, code)

        # test change
        self.evidence.refresh_from_db()
        if modified:
            self.assertEqual(self.evidence.title01, 'Evidence')
        else:
            self.assertEqual(self.evidence.title01, 'Changed')

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_opinion_new(self, override=False, redirect_url=None, code=302, modified=True):
        # test response
        test_url = reverse('theories:opinion-edit', kwargs={'content_pk': self.subtheory.pk})
        post_data = {'true_input': 100}
        response = self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change occured
        opinion = get_or_none(Opinion.objects.all(), content=self.subtheory)
        if modified:
            self.assertIsNotNone(opinion)
            self.assertEqual(opinion.true_input, 100)
            redirect_url = reverse('theories:theory-detail',
                                   kwargs={
                                       'content_pk': opinion.content.pk,
                                       'opinion_pk': opinion.pk
                                   })
            self.verify_redirect(response, redirect_url)
        else:
            self.assertIsNone(opinion)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_opinion_edit(self, override=False, redirect_url=None, code=302, modified=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:theory-detail',
                                   kwargs={
                                       'content_pk': self.my_opinion.content.pk,
                                       'opinion_pk': self.my_opinion.pk
                                   })

        # test response
        test_url = reverse('theories:opinion-edit', kwargs={'content_pk': self.content.pk})
        post_data = {'true_input': 100}
        self.verify_post_response(test_url, redirect_url, post_data, code)

        # test change occured
        self.my_opinion.refresh_from_db()
        if modified:
            self.assertEqual(self.my_opinion.true_input, 100)
        else:
            self.assertNotEqual(self.my_opinion.true_input, 100)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_delete_my_opinion(self,
                                    override=False,
                                    redirect_url=None,
                                    code=302,
                                    deleted=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:theory-detail',
                                   kwargs={'content_pk': self.my_opinion.content.pk})

        # test response
        test_url = reverse('theories:opinion-delete', kwargs={'opinion_pk': self.my_opinion.pk})
        self.verify_post_response(test_url, redirect_url, None, code)

        # test change occured
        self.my_opinion.refresh_from_db()
        if deleted:
            self.assertTrue(self.my_opinion.is_deleted())
        else:
            self.assertFalse(self.my_opinion.is_deleted())

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_delete_bobs_opinion(self,
                                      override=False,
                                      redirect_url=None,
                                      code=403,
                                      deleted=False):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:theory-detail',
                                   kwargs={'content_pk': self.bobs_opinion.content.pk})

        # test response
        test_url = reverse('theories:opinion-delete', kwargs={'opinion_pk': self.bobs_opinion.pk})
        self.verify_post_response(test_url, redirect_url, None, code)

        # test change occured
        opinion = get_or_none(Opinion.objects.all(), id=self.bobs_opinion.pk)
        if deleted:
            self.assertIsNone(opinion)
        else:
            self.assertIsNotNone(opinion)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_copy_opinion(self, override=False, redirect_url=None, code=302, copied=True):
        # setup
        if redirect_url is None:
            redirect_url = reverse('theories:theory-detail',
                                   kwargs={
                                       'content_pk': self.my_opinion.content.pk,
                                       'opinion_pk': self.my_opinion.pk
                                   })
        self.bobs_opinion.true_input = 1234
        self.bobs_opinion.save()

        # test response
        test_url = reverse('theories:opinion-copy', kwargs={'opinion_pk': self.bobs_opinion.pk})
        self.verify_post_response(test_url, redirect_url, None, code)

        # test change occured
        self.my_opinion.refresh_from_db()
        if copied:
            self.assertEqual(self.my_opinion.true_input, 1234)
        else:
            self.assertNotEqual(self.my_opinion.true_input, 1234)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_hide_my_opinion(self, override=False, redirect_url=None, code=302, modified=True):
        # setup
        self.my_opinion.anonymous = False
        self.my_opinion.save()

        # test response
        test_url = reverse('theories:opinion-hide-user', kwargs={'opinion_pk': self.my_opinion.pk})
        self.verify_post_response(test_url, redirect_url, None, code)

        # test change occured
        self.my_opinion.refresh_from_db()
        if modified:
            self.assertTrue(self.my_opinion.anonymous)
        else:
            self.assertFalse(self.my_opinion.anonymous)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_hide_bobs_opinion(self,
                                    override=False,
                                    redirect_url=None,
                                    code=403,
                                    modified=False):
        # setup
        self.bobs_opinion.anonymous = False
        self.bobs_opinion.save()

        # test response
        test_url = reverse('theories:opinion-hide-user',
                           kwargs={'opinion_pk': self.bobs_opinion.pk})
        self.verify_post_response(test_url, redirect_url, None, code)

        # test change occured
        self.bobs_opinion.refresh_from_db()
        if modified:
            self.assertTrue(self.bobs_opinion.anonymous)
        else:
            self.assertFalse(self.bobs_opinion.anonymous)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_reveal_my_opinion(self,
                                    override=False,
                                    redirect_url=None,
                                    code=302,
                                    modified=True):
        # setup
        self.my_opinion.anonymous = True
        self.my_opinion.save()

        # test response
        test_url = reverse('theories:opinion-reveal-user',
                           kwargs={'opinion_pk': self.my_opinion.pk})
        self.verify_post_response(test_url, redirect_url, None, code)

        # test change occured
        self.my_opinion.refresh_from_db()
        if modified:
            self.assertFalse(self.my_opinion.anonymous)
        else:
            self.assertTrue(self.my_opinion.anonymous)

        # method must be overide
        self.assertTrue(override)

    # ******************************
    # Post - ViewsTestBase
    # ******************************
    def test_post_reveal_bobs_opinion(self,
                                      override=False,
                                      redirect_url=None,
                                      code=403,
                                      modified=False):
        # setup
        self.bobs_opinion.anonymous = True
        self.bobs_opinion.save()

        # test response
        test_url = reverse('theories:opinion-reveal-user',
                           kwargs={'opinion_pk': self.bobs_opinion.pk})
        self.verify_post_response(test_url, redirect_url, None, code)

        # test change occured
        self.bobs_opinion.refresh_from_db()
        if modified:
            self.assertFalse(self.bobs_opinion.anonymous)
        else:
            self.assertTrue(self.bobs_opinion.anonymous)

        # method must be overide
        self.assertTrue(override)
