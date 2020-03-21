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
import logging

from theories.models import Category, Content
from theories.abstract_models import TheoryPointerBase

# *******************************************************************************
# Defines
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
# Methods
# *******************************************************************************


def create_categories():
    """
    Create the set of default categories used by Wiki-O.
    Primarily used for initializing the database.
    """
    for title in CATEGORY_TITLES:
        Category.get(title=title, create=True)


def get_category_suggestions():
    suggestions = ''
    for x in Category.objects.all().values('title'):
        suggestions += x['title'] + ','
    suggestions = suggestions.strip(',')
    return suggestions


def create_reserved_nodes(extra=False):
    """
    Create the set of reserved nodes (so far just 'intuition') used by Wiki-O.

    @details    Primarily used for initializing the database.
    @param[in]  extra (optional, default False): If True, 100 reserved nodes will be created.
    """
    intuition_node, created = Content.objects.get_or_create(
        title01='Intuition',
        node_type=Content.TYPE.EVIDENCE,
    )
    if created:
        LOGGER.info('Created intuition theory node.')
    if extra:
        for i in range(1, 100):
            Content.objects.get_or_create(
                title01='R%d' % i,
                node_type=Content.TYPE.EVIDENCE,
            )


def get_demo_theory():
    """Generator a fake theory and populate it with fake evidence.

    Returns:
        Content: The demo theory.
    """
    theory = Content(node_type=Content.TYPE.THEORY, title01='Demo Theory')
    subtheory = Content(node_type=Content.TYPE.THEORY, title01='Demo Sub-Theory')
    fact = Content(node_type=Content.TYPE.FACT, title01='Demo Fact')
    intuition = Content(node_type=Content.TYPE.EVIDENCE, title01='Demo Intuition')
    theory.id = subtheory.id = fact.id = intuition.id = 0
    theory.saved_nodes = [subtheory, fact, intuition]
    return theory


def get_demo_opinion():
    """Generate a fake opinion.

    Returns:
        TheoryPointerBase: The demo opinion.
    """
    theory = get_demo_theory()
    true_points = random.random()
    false_points = 1.0 - true_points
    opinion = TheoryPointerBase.create(
        content=theory,
        true_points=true_points,
        false_points=false_points,
    )
    return opinion
