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
import inspect
import logging

# *******************************************************************************
# Defines
# *******************************************************************************
DEBUG = False
LOGGER = logging.getLogger('django')

# *******************************************************************************
# Models
# *******************************************************************************


class PointerBase():
    """Abstract manager for accessing and agregating the theory's points.

    Usage: This class can also be used to construct dummy Contents that will not show up in
        the database.

    Attributes:
        content (Content): The theory node.
        saved_true_points (float): Cache for the true points.
        saved_false_points (float): Cache for the fasle points.
    """
    content = None
    saved_true_points = None
    saved_false_points = None

    @classmethod
    def create(cls, content=None, true_points=0.0, false_points=0.0):
        """Generator for constructing instances."""
        new_object = cls()
        new_object.content = content
        new_object.saved_true_points = true_points
        new_object.saved_false_points = false_points
        return new_object

    def check_data_for_errors(self):
        """A helper method for logging errors with the data."""
        pass

    def __str__(self):
        """Pass-through for content."""
        return self.content.__str__()

    def get_node_pk(self):
        """Returns content.pk."""
        return self.content.pk

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

    def is_true(self):
        """Returns true if more points are awarded to true."""
        self.check_data_for_errors()
        return self.true_points() >= self.false_points()

    def is_false(self):
        """Returns true if more points are awarded to false."""
        self.check_data_for_errors()
        return self.false_points() > self.true_points()

    def get_point_range(self):
        """Return the range of true points this object possesses."""
        self.check_data_for_errors()
        return self.true_points(), self.true_points()


class TheoryPointerBase():
    """Abstract manager for accessing and agregating the theory's points.

    Usage: This class can also be used to construct dummy Contents that will not show up in
        the database.

    Attributes:
        theory (Content): The theory.
        saved_true_points (float): Cache for the true points.
        saved_false_points (float): Cache for the fasle points.
        saved_opinions (QuerySet:Opinion): Cache for the theory's opinions.
        saved_nodes (QuerySet:Content): Cache for the the theory's nodes.
        saved_flat_nodes (QuerySet:Content): Cache for the theory's flat nodes.
        saved_point_distribution (list[float]): Cache for the theory's point distribution.
    """
    content = None
    saved_true_points = None
    saved_false_points = None
    saved_opinions = None
    saved_nodes = None
    saved_flat_nodes = None
    saved_point_distribution = None
    altered = False

    @classmethod
    def create(cls, content=None, true_points=0.0, false_points=0.0):
        """Generator for constructing instances."""
        new_object = cls()
        new_object.content = content
        new_object.saved_true_points = true_points
        new_object.saved_false_points = false_points
        return new_object

    def check_data_for_errors(self):
        """A helper method for logging errors with the data."""
        if self.content.is_evidence():
            curframe = inspect.currentframe()
            calframe = inspect.getouterframes(curframe, 2)
            LOGGER.error(
                'TheoryPointerBase.check_data_for_errors: is pointing at evidence (%d). '
                'Problem method: TheoryPointerBase.%s', self.content.pk, calframe[1][3])

    def __str__(self):
        """Pass-through for theory."""
        return self.content.__str__()

    def url(self):
        """Return none. Abstract objects have no data in the db."""

    def compare_url(self, opinion02=None):
        """Return none. Abstract objects have no data in the db."""
        LOGGER.error('TheoryPointerBase.compare_url: There is no url for an abstract object (%s).',
                     str(self))

    def get_node_pk(self):
        """Returns theory.pk."""
        return self.content.pk

    def get_nodes(self):
        """Return a set of saved nodes."""
        self.check_data_for_errors()
        if self.saved_nodes is not None:
            return self.saved_nodes
        return []

    def get_flat_nodes(self):
        """Return a set of saved nodes."""
        self.check_data_for_errors()
        if self.saved_flat_nodes is not None:
            return self.saved_flat_nodes
        return []

    def get_opinions(self):
        """Return a set of saved opinions or pass-through to theory.

        Todo:
            * Depreciate?
        """
        self.check_data_for_errors()
        if self.saved_opinions is not None:
            return self.saved_opinions
        return self.content.get_opinions()

    def get_point_distribution(self):
        """Calculate true/false and facts/other point distribution (use cache if available)."""
        self.check_data_for_errors()
        if self.saved_point_distribution is not None:
            return self.saved_point_distribution
        total_points = 0.0
        distribution = {
            'true_facts': 0.0,
            'true_other': 0.0,
            'false_facts': 0.0,
            'false_other': 0.0
        }
        for evidence in self.get_flat_nodes():
            if evidence.is_verifiable():
                distribution['true_facts'] += evidence.true_points()
                distribution['false_facts'] += evidence.false_points()
            else:
                distribution['true_other'] += evidence.true_points()
                distribution['false_other'] += evidence.false_points()
            total_points += evidence.total_points()
        if total_points > 0:
            distribution['true_facts'] = distribution['true_facts'] / total_points
            distribution['true_other'] = distribution['true_other'] / total_points
            distribution['false_facts'] = distribution['false_facts'] / total_points
            distribution['false_other'] = distribution['false_other'] / total_points
        self.saved_point_distribution = distribution
        return distribution

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

    def is_true(self):
        """Returns true if more points are awarded to true."""
        self.check_data_for_errors()
        return self.true_points() >= self.false_points()

    def is_false(self):
        """Returns true if more points are awarded to false."""
        self.check_data_for_errors()
        return self.false_points() > self.true_points()

    def get_point_range(self):
        """Return the range of true points this object possesses."""
        self.check_data_for_errors()
        return self.true_points(), self.true_points()


class NodePointerBase(PointerBase):
    """Abstract manager for passing through methods to linked content_nodes.

    Todo:
        * Move to seperate file.
    """
    parent = None

    @classmethod
    def create(cls, parent=None, content=None, true_points=0.0, false_points=0.0):
        """Generator for constructing instances."""
        new_object = super().create(content, true_points, false_points)
        new_object.parent = parent
        return new_object

    def get_true_statement(self):
        """Pass-through method."""
        return self.content.get_true_statement()

    def get_false_statement(self):
        """Pass-through method."""
        return self.content.get_false_statement()

    def tag_id(self):
        """Pass-through for content."""
        return self.content.tag_id()

    def about(self):
        """Pass-through for content."""
        return self.content.about()

    def url(self):
        """Return a url pointing to content's root (not node)."""
        return None

    def is_theory(self):
        """Pass-through for content."""
        return self.content.is_theory()

    def is_subtheory(self):
        """Pass-through for content."""
        return self.content.is_subtheory()

    def is_evidence(self):
        """Pass-through for content."""
        return self.content.is_evidence()

    def is_fact(self):
        """Pass-through for content."""
        return self.content.is_fact()

    def is_verifiable(self):
        """Pass-through for content."""
        return self.content.is_verifiable()

    def total_points(self):
        """Returns total points."""
        return self.true_points() + self.false_points()

    def true_percent(self):
        """Calculate the percentage awarded to true with respect all parent nodes.

        The true and true points are flipped when necessary.
        """
        if self.parent.true_points() > 0:
            return self.true_points() / self.parent.true_points()
        return 0.0

    def false_percent(self):
        """Calculate the percentage awarded to false with respect all parent nodes.

        The true and false points are flipped when necessary.
        """
        if self.parent.false_points() > 0:
            return self.false_points() / self.parent.false_points()
        return 0.0

    def true_ratio(self):
        """Calculate the ratio of true points with respect to the total points."""
        if self.total_points() > 0:
            return self.true_points() / self.total_points()
        return 0.0

    def false_ratio(self):
        """Calculate the ratio of false points with respect to the total points."""
        if self.total_points() > 0:
            return self.false_points() / self.total_points()
        return 0.0
