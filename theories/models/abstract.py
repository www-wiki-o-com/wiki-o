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

from core.utils import QuerySetDict

# *******************************************************************************
# Defines
# *******************************************************************************
DEBUG = False
LOGGER = logging.getLogger('django')

# *******************************************************************************
# Models
# *******************************************************************************


class ContentPointer():
    """Abstract manager for accessing and agregating the theory's points.

    Usage: This class can also be used to construct dummy Contents that will not show up in
        the database.

    Attributes:
        content (Content): The theory dependency.
        saved_true_points (float): Cache for the true points.
        saved_false_points (float): Cache for the fasle points.
    """
    content = None

    def __str__(self):
        """Pass-through for content."""
        return self.content.__str__()

    def tag_id(self):
        """Pass-through for content."""
        return self.content.tag_id()

    def about(self):
        """Pass-through for content."""
        return self.content.about()

    def is_theory(self):
        """Pass-through for content."""
        return self.content.is_theory()

    def is_subtheory(self):
        """Pass-through for content."""
        return self.content.is_subtheory()

    def is_evidence(self):
        """Pass-through for content."""
        return self.content.is_evidence()

    def is_verifiable(self):
        """Pass-through for content."""
        return self.content.is_verifiable()

    def is_fact(self):
        """Pass-through for content."""
        return self.content.is_fact()


class SavedDependencies():
    """Abstract manager for accessing and agregating the theory's points.

    Usage: This class can also be used to construct dummy Contents that will not show up in
        the database.

    Attributes:
        saved_dependencies (QuerySet:Content): Cache for the the theory's dependencies.
        saved_flat_dependencies (QuerySet:Content): Cache for the theory's flat dependencies.
    """
    saved_dependencies = None
    saved_flat_dependencies = None

    def save_dependencies(self, dependencies=None):
        # Grab and save entire query set.
        if dependencies is None:
            dependencies = QuerySetDict('content.pk')
        list(dependencies)
        self.saved_dependencies = dependencies

    def save_flat_dependencies(self, flat_dependencies=None):
        # Grab and save entire query set.
        if flat_dependencies is None:
            flat_dependencies = QuerySetDict('content.pk')
        list(flat_dependencies)
        self.saved_flat_dependencies = flat_dependencies

    def get_saved_dependencies(self):
        """Return a set of saved dependencies."""
        if self.saved_dependencies is not None:
            return self.saved_dependencies
        return None

    def get_saved_flat_dependencies(self):
        """Return a set of saved dependencies."""
        if self.saved_flat_dependencies is not None:
            return self.saved_flat_dependencies
        return None


class SavedOpinions():
    """Abstract manager for accessing and agregating the theory's points.

    Usage: This class can also be used to construct dummy Contents that will not show up in
        the database.

    Attributes:
        saved_opinions (QuerySet:Opinion): Cache for the theory's opinions.
    """
    saved_opinions = None

    def save_opinions(self, opinions=None):
        # Grab and save entire query set.
        if opinions is None:
            opinions = QuerySetDict('user.pk')
        list(opinions)
        self.saved_opinions = opinions

    def get_saved_opinions(self):
        """Return a set of saved opinions or pass-through to theory."""
        if self.saved_opinions is not None:
            return self.saved_opinions
        return None


class SavedPoints():
    """Abstract manager for accessing and agregating the theory's points.

    Usage: This class can also be used to construct dummy Contents that will not show up in
        the database.

    Attributes:
        saved_true_points (float): Cache for the true points.
        saved_false_points (float): Cache for the fasle points.
    """
    saved_true_points = None
    saved_false_points = None

    def save_points(self, true_points=None, false_points=None):
        """Generator for constructing instances."""
        if true_points is not None:
            self.saved_true_points = true_points
        if false_points is not None:
            self.saved_false_points = false_points

    def true_points(self):
        """Returns true points."""
        if self.saved_true_points is None:
            return 0.0
        return self.saved_true_points

    def false_points(self):
        """Returns false points."""
        if self.saved_false_points is None:
            return 0.0
        return self.saved_false_points