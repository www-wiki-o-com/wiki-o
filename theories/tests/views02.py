#*******************************************************************************
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
#*******************************************************************************


#*******************************************************************************
# imports
#*******************************************************************************
from . views00 import *



#************************************************************
# Restricted user with data created by bob
#
#
#
#
#
#************************************************************
class Level00UserViews(TestCase, ViewsTestBase):
    fixtures = ['groups.json']

    #******************************
    # Setup - Level00User
    #******************************
    def setUp(self):
        # create user(s)
        self.user = create_test_user(username='testuser', password='1234', level=0)
        self.client.login(username='testuser', password='1234')

        # create data
        super().create_data(user=self.user, created_by=self.user)

    #******************************
    # Login - Level00User
    #******************************
    def test_login(self):
        user = auth.get_user(self.client)
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user, self.user)
        self.assertFalse(user.has_perm('theories.add_theorynode'))
        self.assertFalse(user.has_perm('theories.change_theorynode'))
        self.assertFalse(user.has_perm('theories.delete_theorynode'))

    #******************************
    # GET - Level00User
    #******************************
    def test_get_index(self):
        super().test_get_index(
            override  = True,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_index_category(self):
        super().test_get_index_category(
            override  = True,
            category  = 'legal',
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_activity(self):
        super().test_get_activity(
            override  = True,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_theory_create(self):
        super().test_get_theory_create(
            override  = True,
            code      = 403,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_theory_detail(self):
        super().test_get_theory_detail(
            override  = True,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_theory_edit(self):
        super().test_get_theory_edit(
            override  = True,
            code      = 403,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_theory_merge(self):
        super().test_get_theory_merge(
            override  = True,
            code      = 403,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_theory_backup(self):
        super().test_get_theory_backup(
            override  = True,
            code      = 403,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_theory_restore(self):
        super().test_get_theory_restore(
            override  = True,
            code      = 403,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_theory_activity(self):
        super().test_get_theory_activity(
            override      = True,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_theory_edit_evidence(self):
        super().test_get_theory_edit_evidence(
            override  = True,
            code      = 403,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_theory_edit_subtheories(self):
        super().test_get_theory_edit_subtheories(
            override  = True,
            code      = 403,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_theory_inherit(self):
        super().test_get_theory_inherit(
            override  = True,
            code      = 403,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_evidence_detail(self):
        super().test_get_evidence_detail(
            override  = True,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_evidence_edit(self):
        super().test_get_evidence_edit(
            override  = True,
            code      = 403,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_evidence_merge(self):
        super().test_get_evidence_merge(
            override  = True,
            code      = 403,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_evidence_restore(self):
        super().test_get_evidence_restore(
            override  = True,
            code      = 403,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_evidence_activity(self):
        super().test_get_evidence_activity(
            override      = True,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_opinion_demo(self):
        super().test_get_opinion_demo(
            override  = True,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_opinion_detail(self):
        super().test_get_opinion_detail(
            override  = True,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_my_opinion(self):
        super().test_get_my_opinion(
            override  = True,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_opinion_edit(self):
        super().test_get_opinion_edit(
            override  = True,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_opinion_slug(self):
        super().test_get_opinion_slug(
            override  = True,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_user_vs_user(self):
        super().test_get_user_vs_user(
            override  = True,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_user_vs_slug(self):
        super().test_get_user_vs_slug(
            override  = True,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_slug_vs_user(self):
        super().test_get_slug_vs_user(
            override  = True,
        )

    #******************************
    # GET - Level00User
    #******************************
    def test_get_slug_vs_slug(self):
        super().test_get_slug_vs_slug(
            override  = True,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_create(self):
        super().test_post_theory_create(
            override  = True,
            code      = 403,
            created   = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_edit(self):
        super().test_post_theory_edit(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_merge(self):
        super().test_post_theory_merge(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_backup(self):
        super().test_post_theory_backup(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_delete_backup(self):
        super().test_post_theory_delete_backup(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_edit_evidence(self):
        super().test_post_theory_edit_evidence(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_edit_subtheories(self):
        super().test_post_theory_edit_subtheories(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_new_evidence(self):
        super().test_post_theory_new_evidence(
            override  = True,
            code      = 403,
            created   = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_new_subtheories(self):
        super().test_post_theory_new_subtheories(
            override  = True,
            code      = 403,
            created   = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_inherit(self):
        super().test_post_theory_inherit(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_delete(self):
        super().test_post_theory_delete(
            override  = True,
            code      = 403,
            deleted   = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_convert01(self):
        super().test_post_theory_convert01(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_convert02(self):
        super().test_post_theory_convert02(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_revert(self):
        super().test_post_theory_revert(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_add_to_home(self):
        super().test_post_theory_add_to_home(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_theory_remove_from_home(self):
        super().test_post_theory_remove_from_home(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_evidence_edit(self):
        super().test_post_evidence_edit(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_evidence_merge(self):
        super().test_post_evidence_merge(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_evidence_delete_backup(self):
         super().test_post_evidence_delete_backup(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_evidence_delete(self):
        super().test_post_evidence_delete(
            override  = True,
            code      = 403,
            deleted   = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_evidence_backup(self):
        super().test_post_evidence_backup(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_evidence_convert(self):
        super().test_post_evidence_convert(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_evidence_revert(self):
        super().test_post_evidence_revert(
            override  = True,
            code      = 403,
            modified  = False,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_opinion_new(self):
        super().test_post_opinion_new(
            override  = True,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_opinion_edit(self):
        super().test_post_opinion_edit(
            override  = True,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_delete_my_opinion(self):
        super().test_post_delete_my_opinion(
            override  = True,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_delete_bobs_opinion(self):
        super().test_post_delete_bobs_opinion(
            override  = True,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_opinion_copy(self):
        super().test_post_opinion_copy(
            override  = True, 
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_hide_my_opinion(self):
        super().test_post_hide_my_opinion(
            override  = True,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_hide_bobs_opinion(self):
        super().test_post_hide_bobs_opinion(
            override  = True,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_reveal_my_opinion(self):
        super().test_post_reveal_my_opinion(
            override  = True,
        )

    #******************************
    # POST - Level00User
    #******************************
    def test_post_reveal_bobs_opinion(self):
        super().test_post_reveal_bobs_opinion(
            override  = True,
        )

