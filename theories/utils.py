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
import re
import random
import logging
import reversion

from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.contrib import auth

from theories.models import Category, TheoryNode


#*******************************************************************************
# defines
#*******************************************************************************
User   = auth.get_user_model()
logger = logging.getLogger(__name__)

CATEGORY_TITLES = [
  'All',
  'Science',
  'Politics',
  'Legal',
  'Health',
  'Pop Culture',
  'Conspiracy',
]


#*******************************************************************************
# methods
#
#
#
#
#
#
#
#
#
#
#*******************************************************************************

#************************************************************
# 
#************************************************************
def get_or_none(objects, **kwargs):
    try:
        return objects.get(**kwargs)
    except:
        return None





#*******************************************************************************
# setup methods
#
#
#
#
#
#
#
#
#
#
#*******************************************************************************


#******************************
# 
#******************************
def create_categories():
    for title in CATEGORY_TITLES:
        category, created = Category.objects.get_or_create(title=title)
        if created:
            logger.info('Created category: %s.' % category)


#******************************
# 
#******************************
def create_reserved_nodes(extra=False):
    intuition_node, created = TheoryNode.objects.get_or_create(
        title01     = 'Intuition.', 
        node_type   = TheoryNode.TYPE.EVIDENCE,
    )
    if created:
        logger.info('Created intuition theory node.')
    if extra:
        for i in range(1,100):
            new_node, created = TheoryNode.objects.get_or_create(
                title01   = 'R%d' % i,            
                node_type = TheoryNode.TYPE.EVIDENCE,
            )




#*******************************************************************************
# testing methods
#
#
#
#
#
#
#
#
#
#
#*******************************************************************************


#************************************************************
# 
#************************************************************
def get_form_data(response, verbose_level=0):

    # balh
    if response.context is None or not hasattr(response.context, 'keys'):
        return None    
    
    # setup
    data = {}
    for content_name in response.context.keys():
        # formsets
        if re.search(r'formset', content_name):
            formset = response.context[content_name]
            
            # formset managmenet data
            form = formset.management_form
            for field in form.fields.keys():
                data['%s-%s' % (form.prefix, field)] = form[field].value()

            # form data
            for form in formset.forms:
                for field in form.fields.keys():
                    if form[field].value() is None:
                        data['%s-%s' % (form.prefix, field)] = ''
                    else:
                        data['%s-%s' % (form.prefix, field)] = form[field].value()

        # forms
        elif re.search(r'form', content_name):
            form = response.context[content_name]
            if not isinstance(form, bool):
                for field in form.fields.keys():
                    if form.prefix is None:
                        data['%s' % (field)] = form[field].value()
                    else:
                        data['%s-%s' % (form.prefix, field)] = form[field].value()

    if verbose_level >= 10:
        for x in data:
            print(160, x, data[x])

    # blah
    return data


#******************************
# 
#******************************
def create_test_theory(title='Theory', created_by=None, backup=False):
    theory = TheoryNode.get_or_create_theory(
      true_title    = title,
      created_by    = created_by,
    )
    if backup:
        theory.save_snapshot(user=created_by)
    return theory


#******************************
# 
#******************************
def create_test_subtheory(parent_theory, title='Sub-Theory', created_by=None, backup=False):
    subtheory = parent_theory.get_or_create_subtheory(
      true_title    = title,
      created_by    = created_by,
    )
    if backup:
        subtheory.save_snapshot(user=created_by)
    return subtheory


#******************************
# 
#******************************
def create_test_evidence(parent_theory, title='Evidence', fact=False, created_by=None, backup=False):
    evidence = parent_theory.get_or_create_evidence(
      title         = title,
      fact          = fact,
      created_by    = created_by,
    )
    if backup:
        evidence.save_snapshot(user=created_by)
    return evidence


#******************************
# 
#******************************
def create_test_opinion(theory, user, true_input=None, false_input=None, force=False, nodes=False):
    opinion = theory.opinions.create(
      user  = user,
    )
    if true_input is not None:
        opinion.true_input  = true_input
    if false_input is not None:
        opinion.false_input = false_input
    if force:
        opinion.force = force
    opinion.save()
    if nodes:
        random.seed(0)
        for theory_node in theory.get_nodes():
            opinion_node = opinion.nodes.create(
                theory_node  = theory_node,
                tt_input     = random.randint(0,100),
                tf_input     = random.randint(0,100),
                ft_input     = random.randint(0,100),
                ff_input     = random.randint(0,100),
            )
    opinion.update_points()
    theory.add_to_stats(opinion)
    return opinion




