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
from nose.tools import nottest
from theories.models import Category, Content

# *******************************************************************************
# Defines
# *******************************************************************************

# *******************************************************************************
# Helper Methods
# *******************************************************************************


def get_or_create_theory(true_title, false_title=None, created_by=None, category='all'):
    """Generator to translate true_title input and etc to class variables."""
    kwargs = {'content_type': Content.TYPE.THEORY, 'title01': true_title}
    if false_title is not None:
        kwargs['title00'] = false_title
    if created_by is not None:
        kwargs['created_by'] = created_by
        kwargs['modified_by'] = created_by
    theory, _created = Content.objects.get_or_create(**kwargs)
    theory.categories.add(Category.get(category))
    return theory


def get_or_create_subtheory(parent_theory, true_title, false_title=None, created_by=None):
    """Generator to translate true_title input and etc to class variables."""
    # Prerequisites
    if not parent_theory.assert_theory():
        return None
    # Get or create.
    kwargs = {'content_type': Content.TYPE.THEORY, 'title01': true_title}
    if false_title is not None:
        kwargs['title00'] = false_title
    if created_by is not None:
        kwargs['created_by'] = created_by
        kwargs['modified_by'] = created_by
    subtheory, _created = Content.objects.get_or_create(**kwargs)
    parent_theory.add_dependency(subtheory)
    return subtheory


def get_or_create_evidence(parent_theory, title, created_by=None, fact=False):
    """Generator to translate title input and etc to class variables."""
    # Prerequisites
    if not parent_theory.assert_theory():
        return None
    # Get or create.
    kwargs = {'content_type': Content.TYPE.EVIDENCE, 'title01': title}
    if fact:
        kwargs['content_type'] = parent_theory.TYPE.FACT
    if created_by is not None:
        kwargs['created_by'] = created_by
        kwargs['modified_by'] = created_by
    evidence, _created = Content.objects.get_or_create(**kwargs)
    parent_theory.add_dependency(evidence)
    return evidence


@nottest
def create_test_theory(title='Theory', created_by=None, backup=False):
    """
    Create a test theory using the input data.

    @details    Primarily used for unit tests.
    @param[in]  title (optional, default 'Theory'): The theory's title.
    @param[in]  created_by (optional, default None): The user that created the theory.
    @param[in]  backup (optional, default False): If True, a backup is also created.
    """
    theory = get_or_create_theory(true_title=title, created_by=created_by)
    if backup:
        theory.save_snapshot(user=created_by)
    return theory


@nottest
def create_test_subtheory(parent_theory, title='Sub-Theory', created_by=None, backup=False):
    """
    Create a test sub-theory using the input data.

    @details    Primarily used for unit tests.
    @param[in]  parent_theory: The Content that is to be this theory's parent.
    @param[in]  title (optional, default 'Sub-Theory'): The sub-theory's title.
    @param[in]  created_by (optional, default None): The user that created the theory.
    @param[in]  backup (optional, default False): If True, a backup is also created.
    """
    subtheory = get_or_create_subtheory(
        parent_theory,
        true_title=title,
        created_by=created_by,
    )
    if backup:
        subtheory.save_snapshot(user=created_by)
    return subtheory


@nottest
def create_test_evidence(parent_theory,
                         title='Evidence',
                         fact=False,
                         created_by=None,
                         backup=False):
    """
    Create a test evidence using the input data.

    @details    Primarily used for unit tests.
    @param[in]  parent_theory: The Content that is to be this theory's parent.
    @param[in]  title (optional, default 'Evidence'): The evidence's title.
    @param[in]  created_by (optional, default None): The user that created the theory.
    @param[in]  backup (optional, default False): If True, a backup is also created.
    """
    evidence = get_or_create_evidence(
        parent_theory,
        title=title,
        fact=fact,
        created_by=created_by,
    )
    if backup:
        evidence.save_snapshot(user=created_by)
    return evidence


@nottest
def create_test_opinion(content,
                        user,
                        true_input=None,
                        false_input=None,
                        force=False,
                        dependencies=False):
    """
    Create an opinion using the input data.

    @details    Primarily used for unit tests.
    @param[in]  theory: The Content that this opinion is based on.
    @param[in]  true_input (optional, default None): The true points that are to be assigned to this opinion.
    @param[in]  false_input (optional, default None): The false points that are to be assigned to this opinion.
    @param[in]  force (optional, default False): If True, the true and false ratios will be preserved, otherwise they will be determined by the opinion's dependencies.
    @param[in]  dependencies (optional, default False): If True, a random set of dependencies will be added to the opinion.
    """
    opinion = content.opinions.create(user=user,)
    if true_input is not None:
        opinion.true_input = true_input
    if false_input is not None:
        opinion.false_input = false_input
    if force:
        opinion.force = force
    opinion.save()
    if dependencies:
        random.seed(0)
        for child_content in content.get_dependencies():
            opinion.dependencies.create(
                content=child_content,
                tt_input=random.randint(0, 100),
                tf_input=random.randint(0, 100),
                ft_input=random.randint(0, 100),
                ff_input=random.randint(0, 100),
            )
    opinion.update_points()
    content.add_to_stats(opinion)
    return opinion
