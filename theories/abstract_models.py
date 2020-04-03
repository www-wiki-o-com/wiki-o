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
from core.utils import get_or_none, QuerySetDict

# *******************************************************************************
# Defines
# *******************************************************************************
DEBUG = False
LOGGER = logging.getLogger('django')

# *******************************************************************************
# Models
# *******************************************************************************


class ContentPointerBase():
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


class OpinionBase(ContentPointerBase, SavedPoints, SavedDependencies):
    """Abstract manager for accessing and agregating the theory's points.

    Usage: This class can also be used to construct dummy Contents that will not show up in
        the database.

    Inherited Attributes:
        content (Content): The content.
        saved_true_points (float): Cache for the true points.
        saved_false_points (float): Cache for the fasle points.
        saved_opinions (QuerySet:Opinion): Cache for the theory's opinions.
        saved_dependencies (QuerySet:Content): Cache for the the theory's dependencies.
        saved_flat_dependencies (QuerySet:Content): Cache for the theory's flat dependencies.
        saved_point_distribution (list[float]): Cache for the theory's point distribution.
    """
    dependencies = None
    flat_dependencies = None
    saved_point_distribution = None

    @classmethod
    def create(cls,
               content=None,
               true_points=0.0,
               false_points=0.0,
               dependencies=None,
               flat_dependencies=None):
        """Generator for constructing instances."""
        new_object = cls()
        new_object.content = content
        new_object.save_points(true_points, false_points)
        new_object.save_dependencies(dependencies)
        new_object.save_flat_dependencies(flat_dependencies)
        return new_object

    def check_for_errors(self):
        """A helper method for logging errors with the data."""
        if self.content.is_evidence():
            curframe = inspect.currentframe()
            calframe = inspect.getouterframes(curframe, 2)
            LOGGER.error(
                'OpinionBase.check_for_errors: is pointing at evidence (%d). '
                'Problem method: OpinionBase.%s', self.content.pk, calframe[1][3])

    def url(self):
        """Return none. Abstract objects have no data in the db."""

    def compare_url(self, opinion02=None):
        """Return none. Abstract objects have no data in the db."""
        LOGGER.error('TheoryPointerBase.compare_url: There is no url for an abstract object (%s).',
                     str(self))

    def get_dependency(self, content, create=False):
        """Return the stats dependency for the corresponding content (optionally, create the stats dependency)."""
        # Get dependencies.
        dependencies = self.get_dependencies()
        # Get dependency.
        dependency = get_or_none(dependencies, content=content)
        if dependency is None and create:
            if self.dependencies is None:
                dependency = OpinionDependencyBase.create(
                    parent=self,
                    content=content,
                )
            else:
                dependency, _created = self.dependencies.get_or_create(content=content)
            # Add to cache (if it exists).
            saved_dependencies = self.get_saved_dependencies()
            if saved_dependencies is not None:
                if isinstance(saved_dependencies, QuerySetDict):
                    saved_dependencies.add(dependency)
                else:
                    self.save_dependencies(self.dependencies.all())
        return dependency

    def get_dependencies(self, cache=False):
        """Return the stats dependency for the theory (use cache if available)."""
        # Check cache first.
        dependencies = self.get_saved_dependencies()
        if dependencies is None and self.dependencies is not None:
            if self.dependencies is not None:
                dependencies = self.dependencies.all()
            if cache:
                self.save_dependencies(dependencies)
        return dependencies

    def get_flat_dependency(self, content, create=False):
        """Return the flat stats dependency for the input content (optionally, create the dependency)."""
        # Get dependencies.
        flat_dependencies = self.get_flat_dependencies()
        # Get dependency.
        dependency = get_or_none(flat_dependencies, content=content)
        if dependency is None and create:
            if self.flat_dependencies is None:
                dependency = OpinionDependencyBase.create(
                    parent=self,
                    content=content,
                )
                print(272, self, content)
            else:
                dependency, _created = self.flat_dependencies.get_or_create(content=content)
            # Add to cache (if it exists).
            saved_flat_dependencies = self.get_saved_flat_dependencies()
            if saved_flat_dependencies is not None:
                if isinstance(saved_flat_dependencies, QuerySetDict):
                    saved_flat_dependencies.add(dependency)
                else:
                    self.save_flat_dependencies(self.flat_dependencies.all())
        return dependency

    def get_flat_dependencies(self, cache=False):
        """Return a query set of the flat dependencies/nested evidence (use cache if available)."""
        # Check cache first.
        flat_dependencies = self.get_saved_flat_dependencies()
        if flat_dependencies is None and self.flat_dependencies is not None:
            flat_dependencies = self.flat_dependencies.all()
            if cache:
                self.save_flat_dependencies(flat_dependencies)
        return flat_dependencies

    def get_point_range(self):
        """Return the range of true points this object possesses."""
        self.check_for_errors()
        return self.true_points(), self.true_points()

    def get_point_distribution(self):
        """Calculate true/false and facts/other point distribution (use cache if available)."""
        self.check_for_errors()
        if self.saved_point_distribution is not None:
            return self.saved_point_distribution
        total_points = 0.0
        distribution = {
            'true_facts': 0.0,
            'true_other': 0.0,
            'false_facts': 0.0,
            'false_other': 0.0
        }
        for evidence in self.get_flat_dependencies():
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

    def is_true(self):
        """Returns true if more points are awarded to true."""
        return self.true_points() >= self.false_points()

    def is_false(self):
        """Returns true if more points are awarded to false."""
        return self.false_points() > self.true_points()


class OpinionDependencyBase(ContentPointerBase, SavedPoints):
    """Abstract manager for passing through methods to linked theory_dependencies.

    Todo:
        * Move to seperate file.
    """
    parent = None

    @classmethod
    def create(cls, parent=None, content=None, true_points=0.0, false_points=0.0):
        """Generator for constructing instances."""
        new_object = cls()
        new_object.parent = parent
        new_object.content = content
        new_object.save_points(true_points, false_points)
        return new_object

    def total_points(self):
        """Returns total points."""
        return self.true_points() + self.false_points()

    def true_percent(self):
        """Calculate the percentage awarded to true with respect all parent dependencies.

        The true and true points are flipped when necessary.
        """
        if self.parent.true_points() > 0:
            return self.true_points() / self.parent.true_points()
        return 0.0

    def false_percent(self):
        """Calculate the percentage awarded to false with respect all parent dependencies.

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
