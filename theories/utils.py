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
# methods
# *******************************************************************************


def create_categories():
    """
    Create the set of default categories used by Wiki-O.
    Primarily used for initializing the database.
    """
    for title in CATEGORY_TITLES:
        category, created = Category.objects.get_or_create(title=title)
        if created:
            LOGGER.info('Created category: %s.', category)


def create_reserved_nodes(extra=False):
    """
    Create the set of reserved nodes (so far just 'intuition') used by Wiki-O.

    @details    Primarily used for initializing the database.
    @param[in]  extra (optional, default False): If True, 100 reserved nodes will be created.
    """
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


def create_test_theory(title='Theory', created_by=None, backup=False):
    """
    Create a test theory using the input data.

    @details    Primarily used for unit tests.
    @param[in]  title (optional, default 'Theory'): The theory's title.
    @param[in]  created_by (optional, default None): The user that created the theory.
    @param[in]  backup (optional, default False): If True, a backup is also created.
    """
    theory = TheoryNode.get_or_create_theory(
        true_title=title,
        created_by=created_by,
    )
    if backup:
        theory.save_snapshot(user=created_by)
    return theory


def create_test_subtheory(parent_theory, title='Sub-Theory', created_by=None, backup=False):
    """
    Create a test sub-theory using the input data.

    @details    Primarily used for unit tests.
    @param[in]  parent_theory: The TheoryNode that is to be this theory's parent.
    @param[in]  title (optional, default 'Sub-Theory'): The sub-theory's title.
    @param[in]  created_by (optional, default None): The user that created the theory.
    @param[in]  backup (optional, default False): If True, a backup is also created.
    """
    subtheory = parent_theory.get_or_create_subtheory(
        true_title=title,
        created_by=created_by,
    )
    if backup:
        subtheory.save_snapshot(user=created_by)
    return subtheory


def create_test_evidence(parent_theory, title='Evidence', fact=False, created_by=None, backup=False):
    """
    Create a test evidence using the input data.

    @details    Primarily used for unit tests.
    @param[in]  parent_theory: The TheoryNode that is to be this theory's parent.
    @param[in]  title (optional, default 'Evidence'): The evidence's title.
    @param[in]  created_by (optional, default None): The user that created the theory.
    @param[in]  backup (optional, default False): If True, a backup is also created.
    """
    evidence = parent_theory.get_or_create_evidence(
        title=title,
        fact=fact,
        created_by=created_by,
    )
    if backup:
        evidence.save_snapshot(user=created_by)
    return evidence


def create_test_opinion(theory, user, true_input=None, false_input=None, force=False, nodes=False):
    """
    Create an opinion using the input data.

    @details    Primarily used for unit tests.
    @param[in]  theory: The TheoryNode that this opinion is based on.
    @param[in]  true_input (optional, default None): The true points that are to be assigned to this opinion.
    @param[in]  false_input (optional, default None): The false points that are to be assigned to this opinion.
    @param[in]  force (optional, default False): If True, the true and false ratios will be preserved, otherwise they will be determined by the opinion's dependencies.
    @param[in]  nodes (optional, default False): If True, a random set of dependencies will be added to the opinion.
    """
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
