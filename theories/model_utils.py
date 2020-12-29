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
import logging

from django.db.models import Q
from django.urls import reverse
from notifications.signals import notify

from core.utils import get_or_none, notify_if_unique
from theories.models.opinions import Opinion, OpinionDependency
from theories.models.statistics import Stats
from users.models import User

# *******************************************************************************
# Defines
# *******************************************************************************
DEBUG = False
LOGGER = logging.getLogger('django')

# *******************************************************************************
# Models
# *******************************************************************************


def merge_content(content01, content02, user=None):
    """Merge this theory dependency with another, by absorbing the other dependency.

    Args:
        content01 ([type]): [description]
        content02 ([type]): [description]
        user ([type], optional): [description]. Defaults to None.

    Returns:
        [type]: [description]

    Todo:
        * Delete stats.
    """
    # Error checking
    if content01.content_type != content02.content_type:
        LOGGER.error('models.merge: Cannot merge content of different type (pk01=%d, pk02=%d).',
                     content01.pk, content02.pk)
        return False
    # Setup
    if user is None:
        user = User.get_system_user()
    # Theories
    if content01.is_theory():
        # Dependencies
        dependencies02 = content02.get_dependencies().exclude(pk=content01.pk)
        flat_dependencies02 = content02.get_flat_dependencies().exclude(pk=content01.pk)
        content01.dependencies.add(*dependencies02)
        content01.flat_dependencies.add(*flat_dependencies02)
    # Parents
    for parent in content02.parents.filter(~Q(pk=content01.pk)):
        parent.add_dependency(content01)
    # Opinion dependencies
    changed_theories = []
    for opinion_dependency02 in content02.opinion_dependencies.all():
        opinion = opinion_dependency02.parent
        opinion_dependency01 = get_or_none(opinion.get_dependencies(), content=content01)
        if opinion_dependency01 is None:
            Stats.remove(opinion, cache=True, save=False)
            opinion_dependency02.content = content01
            opinion_dependency02.save()
            Stats.add(opinion, cache=True, save=False)
            changed_theories.append(opinion.content)
        else:
            # notifications
            log = {}
            log['sender'] = user
            log['recipient'] = opinion.user
            log['verb'] = '<# object.url "{{ object }}" has gone through a merge that affects your opinion. #>'
            log['description'] = 'We apologize for the inconvenience. Please review your <# target.url opinion #> and adjust as necessary.'
            log['action_object'] = content01
            log['target'] = opinion
            log['level'] = 'warning'
            notify_if_unique(opinion.user, log)
    # Save changes
    for theory in changed_theories:
        theory.save_stats()
    # Delete
    content02.delete(user)
    return True


def swap_true_false(content, user=None):
    """Swap true false titles of theory and permeate the changes to opinions and stats.

    Args:
        user ([type], optional): [description]. Defaults to None.

    Returns:
        [type]: [description]

    Todo:
        * Improve stats calculation.
        * Add assert.
    """
    # Error checking
    if not content.assert_theory():
        return False
    # Setup
    if user is None:
        user = User.get_system_user()
    # Theory dependency
    content.title00, content.title01 = content.title01, content.title00
    content.save()
    # Opinions
    for opinion in content.get_opinions():
        opinion.swap_true_false()
        notify.send(
            sender=user,
            recipient=opinion.user,
            verb=
            """<# object.url The theory, "{{ object }}" has had its true and false titles swapped. #>""",
            description='This should not effect your <# target.url opinion #> in anyway.',
            action_object=content,
            target=opinion,
            level='warning',
        )
    # Stats
    for stats in Stats.get(content):
        stats.swap_true_false()
    return True


def convert_content_type(content, user=None, verifiable=False):
    """Converts a theory to evidence and vise-a-versa.

    Args:
        user ([type], optional): [description]. Defaults to None.
        verifiable (bool, optional): [description]. Defaults to False.

    Returns:
        [type]: [description]

    Todo:
        * Allow evidence to have user opinions but not editable ones.
        * Go over notification logic.
    """
    # setup
    if user is None:
        user = User.get_system_user()
    if content.is_theory():
        # error checking
        if content.parents.count() == 0 or content.is_root():
            LOGGER.error('models.convert: Cannot convert a root theory to evidence (pk=%d).',
                         content.pk)
            return False
        # inherit dependencies
        for parent_theory in content.get_parent_theories():
            for theory_dependency in content.get_dependencies():
                parent_theory.add_dependency(theory_dependency)
        # clear stats
        for stats in Stats.get(content):
            stats.delete()
        # convert theory dependency
        if verifiable:
            content.content_type = content.TYPE.FACT
        else:
            content.content_type = content.TYPE.EVIDENCE
        content.dependencies.clear()
        content.flat_dependencies.clear()
    else:
        content.content_type = content.TYPE.THEORY
    content.save(user)
    # notifications (opinions)
    if content.is_theory():
        for opinion in content.get_opinions():
            notify.send(
                sender=user,
                recipient=opinion.user,
                verb='<# object.url The theory, "{{ object }}" has been converted to evidence. #>',
                description='This change has rendered your <# target.url opinion #> unnecessary.',
                action_object=content,
                target=opinion,
                level='warning',
            )
    # notifications (opinion_dependencies)
    for opinion_dependency in content.opinion_dependencies.all():
        print(439, opinion_dependency, opinion_dependency.parent, opinion_dependency.parent.user)
        if content.is_evidence():
            verb = '<# object.url The theory, "{{ object }}" has been converted to evidence. #>'
        else:
            verb = '<# object.url The evidence, "{{ object }}" has been converted to a sub-theory. #>'
        notify.send(
            sender=user,
            recipient=opinion_dependency.parent.user,
            verb=verb,
            description='This change affects your <# target.url opinion #> of {{ target }}.',
            action_object=content,
            target=opinion_dependency.parent,
            level='warning',
        )
    return True


def get_compare_url(opinion01, opinion02=None):
    # Setup
    content = opinion01.content

    # Get opinion01 id
    pk01 = slug01 = None
    if isinstance(opinion01, Opinion):
        pk01 = opinion01.pk
    elif isinstance(opinion01, Stats):
        slug01 = opinion01.get_slug()

    # Get opinion02 id
    pk02 = slug02 = None
    if opinion02 is None:
        slug02 = 'all'
    elif isinstance(opinion02, Opinion):
        pk02 = opinion02.pk
    elif isinstance(opinion02, Stats):
        slug02 = opinion02.get_slug()

    # Generate url
    if pk01 and pk02:
        url = reverse('theories:opinion-compare',
                      kwargs={
                          'content_pk': content.pk,
                          'opinion_pk01': pk01,
                          'opinion_pk02': pk02
                      })
    elif pk01 and slug02:
        url = reverse('theories:opinion-compare',
                      kwargs={
                          'content_pk': content.pk,
                          'opinion_pk01': pk01,
                          'opinion_slug02': slug02
                      })
    elif slug01 and pk02:
        url = reverse('theories:opinion-compare',
                      kwargs={
                          'content_pk': content.pk,
                          'opinion_slug01': slug01,
                          'opinion_pk02': pk02
                      })
    elif slug01 and slug02:
        url = reverse('theories:opinion-compare',
                      kwargs={
                          'content_pk': content.pk,
                          'opinion_slug01': slug01,
                          'opinion_slug02': slug02
                      })
    else:
        url = ''

    # Return
    return url


def copy_opinion(opinion, user, recursive=False, path=None, verbose_level=0):
    """Copy opinion to user's opinion"""
    # Debug
    if verbose_level > 0:
        print("opinion.copy()")

    # setup
    if path is None:
        path = []
    path.append(opinion.content.pk)
    theory = opinion.content

    # delete existing opinion
    user_opinion = get_or_none(theory.get_opinions(), user=user)
    if user_opinion is not None:
        Stats.remove(user_opinion, cache=True, save=False)
        user_opinion.delete()

    # new opinion
    user_opinion, _created = theory.opinions.get_or_create(user=user)
    user_opinion.true_input = opinion.true_input
    user_opinion.false_input = opinion.false_input
    user_opinion.force = opinion.force
    user_opinion.save()

    # populate dependencies
    for opinion_dependency in opinion.get_dependencies():
        OpinionDependency.objects.get_or_create(
            parent=user_opinion,
            content=opinion_dependency.content,
            tt_input=opinion_dependency.tt_input,
            tf_input=opinion_dependency.tf_input,
            ft_input=opinion_dependency.ft_input,
            ff_input=opinion_dependency.ff_input,
        )

    # points
    user_opinion.update_points()

    # recursive
    if recursive:
        for subtheory in opinion.get_theory_subtheories():
            root_opinion = subtheory.get_root()
            if root_opinion is not None and root_opinion.content.pk not in path:
                copy_opinion(root_opinion, user, recursive=True)

    # stats
    Stats.add(user_opinion, cache=True, save=False)
    Stats.save(user_opinion)

    # Debug
    if verbose_level > 0:
        print("opinion.copy()")
    return user_opinion
