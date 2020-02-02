"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       theories/utils.py
@brief      A collection of app specific utility methods/classes
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# imports
# *******************************************************************************
import random
import logging
from django.contrib import auth

from theories.models import Category, TheoryNode


# *******************************************************************************
# defines
# *******************************************************************************
LOGGER = logging.getLogger(__name__)

CATEGORY_TITLES = [
    'All',
    'Science',
    'Politics',
    'Legal',
    'Health',
    'Pop Culture',
    'Conspiracy',
]


# *******************************************************************************
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
# *******************************************************************************


# ******************************
#
# ******************************
def create_categories():
    for title in CATEGORY_TITLES:
        category, created = Category.objects.get_or_create(title=title)
        if created:
            LOGGER.info('Created category: %s.' % category)


# ******************************
#
# ******************************
def create_reserved_nodes(extra=False):
    intuition_node, created = TheoryNode.objects.get_or_create(
        title01='Intuition.',
        node_type=TheoryNode.TYPE.EVIDENCE,
    )
    if created:
        LOGGER.info('Created intuition theory node.')
    if extra:
        for i in range(1, 100):
            new_node, created = TheoryNode.objects.get_or_create(
                title01='R%d' % i,
                node_type=TheoryNode.TYPE.EVIDENCE,
            )


# *******************************************************************************
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
# *******************************************************************************



# ******************************
#
# ******************************
def create_test_theory(title='Theory', created_by=None, backup=False):
    theory = TheoryNode.get_or_create_theory(
        true_title=title,
        created_by=created_by,
    )
    if backup:
        theory.save_snapshot(user=created_by)
    return theory


# ******************************
#
# ******************************
def create_test_subtheory(parent_theory, title='Sub-Theory', created_by=None, backup=False):
    subtheory = parent_theory.get_or_create_subtheory(
        true_title=title,
        created_by=created_by,
    )
    if backup:
        subtheory.save_snapshot(user=created_by)
    return subtheory


# ******************************
#
# ******************************
def create_test_evidence(parent_theory, title='Evidence', fact=False, created_by=None, backup=False):
    evidence = parent_theory.get_or_create_evidence(
        title=title,
        fact=fact,
        created_by=created_by,
    )
    if backup:
        evidence.save_snapshot(user=created_by)
    return evidence


# ******************************
#
# ******************************
def create_test_opinion(theory, user, true_input=None, false_input=None, force=False, nodes=False):
    opinion = theory.opinions.create(
        user=user,
    )
    if true_input is not None:
        opinion.true_input = true_input
    if false_input is not None:
        opinion.false_input = false_input
    if force:
        opinion.force = force
    opinion.save()
    if nodes:
        random.seed(0)
        for theory_node in theory.get_nodes():
            opinion_node = opinion.nodes.create(
                theory_node=theory_node,
                tt_input=random.randint(0, 100),
                tf_input=random.randint(0, 100),
                ft_input=random.randint(0, 100),
                ff_input=random.randint(0, 100),
            )
    opinion.update_points()
    theory.add_to_stats(opinion)
    return opinion
