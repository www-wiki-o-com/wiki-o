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
import math
import random

from theories.models import NodePointerBase, Opinion
from theories.graphs.shapes import Colour, Text
from theories.graphs.spring_shapes import Direction, Ring, EvidenceShape, SubtheoryShape, Wall
from theories.utils import get_demo_opinion

# *******************************************************************************
# Diagrams
#
#
#
#
#
#
# *******************************************************************************


class OpinionVennDiagram():
    """A class for drawing Venn-diagrams."""

    # Constants
    DEFAULT_CONFIG = {'radius': 150, 'shape_area': 0.6 * 150**2}
    DEFAULT_BOARDER = {'top': 60, 'bottom': 30, 'left': 100, 'right': 100}

    def __init__(self, opinion, flat=False, bottom_text=None, config=None, boarder=None):
        """Create a Venn-diagram that visualizes the opinion's nodes."""
        self.opinion = opinion
        self.flat = flat
        self.bottom_text = bottom_text
        if config is None:
            self.config = self.DEFAULT_CONFIG
        else:
            self.config = config
        if boarder is None:
            self.boarder = self.DEFAULT_BOARDER
        else:
            self.boarder = boarder
        self.true_set = []
        self.false_set = []
        self.outside_set = []
        self.intersection_set = []
        self.true_ring = None
        self.false_ring = None
        self.text = []
        self.true_shapes = []
        self.false_shapes = []
        self.intersection_shapes = []
        self.outside_shapes = []
        self.in_boundry_shapes = []
        self.out_boundry_shapes = []
        self.construct()

    def construct(self):
        """Construct the diagram."""
        self.calc_membership()
        self.create_rings()
        self.create_shapes()
        self.fix_overlap01()

        self.create_outside_shapes()
        self.create_ledgend()
        self.create_boundary_shapes()
        self.fix_overlap02()

    def __str__(self):
        """Output debug text for diagram (not yet implemented).

        Returns:
            str: Blank
        """
        return ''

    def calc_membership(self):
        """Group opinion nodes into: true, false, true & false, and neither."""
        # Setup
        self.true_set = []
        self.false_set = []
        self.outside_set = []
        self.intersection_set = []
        if self.flat:
            nodes = self.opinion.get_flat_nodes()
        else:
            nodes = self.opinion.get_nodes()

        # Populate membership
        for node in nodes:
            if node.total_points() < 0.01:
                if node.total_points() > 0:
                    self.outside_set.append(node)
            elif node.true_ratio() >= 0.66:
                self.true_set.append(node)
            elif node.false_ratio() >= 0.66:
                self.false_set.append(node)
            else:
                self.intersection_set.append(node)

    def create_rings(self):
        """Create the true and false rings."""
        # If the intersection set is empty, fix the rings in place.
        r = self.config['radius']
        if len(self.intersection_set) == 0:
            self.true_ring = Ring(-0.85 * r, 0.0, r, x_max=-0.35 * r)
            self.false_ring = Ring(0.85 * r, 0.0, r, x_min=0.35 * r)
        # Otherwise, overlap the rings.
        else:
            self.true_ring = Ring(-0.75 * r, 0.0, r, x_max=-0.35 * r)
            self.false_ring = Ring(0.75 * r, 0.0, r, x_min=0.35 * r)

    def create_ledgend(self):
        """Create legend text."""
        self.text = []
        r = self.config['radius']
        boarder = self.boarder
        self.text.append(
            Text('True',
                 x=self.true_ring.x,
                 y=self.true_ring.y - 1.0 * 13 / 12 * r,
                 size=40,
                 colour=Colour.BLACK,
                 bold=True))
        self.text.append(
            Text('False',
                 x=self.false_ring.x,
                 y=self.true_ring.y - 1.0 * 13 / 12 * r,
                 size=40,
                 colour=Colour.RED,
                 bold=True))
        if self.bottom_text is not None:
            self.text.append(
                Text(self.bottom_text,
                     x=(self.true_ring.x + self.false_ring.x) / 2,
                     y=0.95 * r + boarder['bottom']))

    def create_shapes(self):
        """Create the evidence and sub-theory shapes (within the true and false sets)."""
        # Setup
        random.seed(0)
        r = self.config['radius']

        # Create the set of true shapes (randomly place the shape inside the true ring)
        self.true_shapes = []
        for node in self.true_set:
            r = math.sqrt(random.random()) * r
            theta = math.radians(random.randint(0, 360))
            x = self.true_ring.x + r * math.cos(theta)
            y = self.true_ring.y + r * math.sin(theta)
            area = self.config['shape_area'] * node.total_points()
            if node.is_theory():
                self.true_shapes.append(SubtheoryShape(node, x, y, area))
            elif node.is_evidence():
                self.true_shapes.append(EvidenceShape(node, x, y, area))

        # Create the set of shapes in the intersection (randomly place in the intersection)
        self.intersection_shapes = []
        for node in self.intersection_set:
            r = math.sqrt(random.random()) * r
            theta = math.radians(random.randint(0, 360))
            x = (self.true_ring.x + self.false_ring.x) / 2 + r * math.cos(theta)
            y = (self.true_ring.y + self.false_ring.y) / 2 + r * math.sin(theta)
            area = self.config['shape_area'] * node.total_points()
            if node.is_theory():
                self.intersection_shapes.append(SubtheoryShape(node, x, y, area))
            elif node.is_evidence():
                self.intersection_shapes.append(EvidenceShape(node, x, y, area))

        # Create the set of false shapes (randomly place the shape inside the false ring)
        self.false_shapes = []
        for node in self.false_set:
            r = math.sqrt(random.random()) * r
            theta = math.radians(random.randint(0, 360))
            x = self.false_ring.x + r * math.cos(theta)
            y = self.false_ring.y + r * math.sin(theta)
            area = self.config['shape_area'] * node.total_points()
            if node.is_theory():
                self.false_shapes.append(SubtheoryShape(node, x, y, area))
            elif node.is_evidence():
                self.false_shapes.append(EvidenceShape(node, x, y, area))

    def create_outside_shapes(self):
        """Create evidence and sub-theory shapes that falls outside of the true and false sets."""
        random.seed(0)
        r = self.config['radius']
        boarder = self.boarder
        x_min = self.true_ring.x - r - boarder['left']
        x_max = self.false_ring.x + r + boarder['right']
        x_width = x_max - x_min
        y_min = self.true_ring.y + r + boarder['top']
        y_max = self.true_ring.y - r - boarder['bottom']
        y_width = y_max - y_min

        # Create the shapes outside both the true and false rings (radomly place them inside the
        # frame, the springs will push them outside of the rings).
        self.outside_shapes = []
        for node in self.outside_set:
            x = random.random() * x_width + x_min
            y = random.random() * y_width + y_min
            area = self.config['shape_area'] * node.total_points()
            if node.is_theory():
                self.outside_shapes.append(SubtheoryShape(node, x, y, area))
            elif node.is_evidence():
                self.outside_shapes.append(EvidenceShape(node, x, y, area))

    def create_boundary_shapes(self):
        """Create boundary shapes to confine the shapes to the view port."""
        # Setup
        r = self.config['radius']
        x_min = self.true_ring.x - r - self.boarder['left']
        x_max = self.false_ring.x + r + self.boarder['right']
        y_max = self.true_ring.y - r - self.boarder['top']
        y_min = self.true_ring.y + r + self.boarder['bottom']
        x_width = x_max - x_min

        # Construt walls at the top and bottom of the image frame and a circle to keep the
        # shapes horizontally in the frame.
        self.in_boundry_shapes = []
        self.in_boundry_shapes.append(Wall(None, y_max))
        self.in_boundry_shapes.append(Wall(None, y_min))
        self.in_boundry_shapes.append(Ring((x_min + x_max) / 2, self.true_ring.y, x_width / 2))

        # Construct a circle to avoid the middle of the figure and the true and false text
        # (only applies to shapes outside the two rings).
        x02 = (self.true_ring.x + self.false_ring.x) / 2
        y02 = self.true_ring.y
        r02 = (self.false_ring.x - self.true_ring.x) / 2 + 1 * r
        self.out_boundry_shapes = [Ring(x02, y02, r02)]

    def fix_overlap01(self):
        """Move the inside shapes around to avoid overlap."""
        # Setup
        shapes = []
        if len(self.intersection_shapes) > 0:
            shapes.append({
                'prop': self.true_shapes,
                'in': [self.true_ring],
                'out': self.true_shapes + [self.false_ring]
            })
            shapes.append({
                'prop': self.false_shapes,
                'in': [self.false_ring],
                'out': self.false_shapes + [self.true_ring]
            })
            shapes.append({
                'prop': self.intersection_shapes,
                'in': [self.true_ring, self.false_ring],
                'out': self.intersection_shapes
            })
            shapes.append({
                'prop': [self.true_ring],
                'in': self.true_shapes + self.intersection_shapes,
                'out': self.false_shapes
            })
            shapes.append({
                'prop': [self.false_ring],
                'in': self.false_shapes + self.intersection_shapes,
                'out': self.true_shapes
            })
        else:
            shapes.append({
                'prop': self.true_shapes,
                'in': [self.true_ring],
                'out': self.true_shapes + [self.false_ring]
            })
            shapes.append({
                'prop': self.false_shapes,
                'in': [self.false_ring],
                'out': self.false_shapes + [self.true_ring]
            })

        # Propagate (self organize)
        self.propagate(shapes)

    def fix_overlap02(self):
        """Move the outside shapes around to avoid overlap."""
        # Setup
        shapes = [{
            'prop': self.outside_shapes,
            'in': self.in_boundry_shapes,
            'out': self.out_boundry_shapes + self.outside_shapes
        }]
        for shape in [self.true_ring, self.false_ring]:
            shape.reset_spring_constant()

        # Propagate
        self.propagate(shapes)

    def propagate(self, shapes):
        """Incrementally propagate the spring-class shapes to avoid overlap.

        Args:
            shapes (list(dict('prop':, 'in':, 'out'))): A list of all the shapes to propigate.
        """
        for i in range(100):
            max_step = 0.0
            for shape_set in shapes:
                for shape01 in shape_set['prop']:
                    total_x_force = 0.0
                    total_y_force = 0.0
                    for shape02 in shape_set['out']:
                        if shape02 != shape01:
                            f_x, f_y = shape02.get_spring_force(shape01, direction=Direction.OUT)
                            total_x_force += f_x
                            total_y_force += f_y
                    for shape02 in shape_set['in']:
                        f_x, f_y = shape02.get_spring_force(shape01, direction=Direction.IN)
                        total_x_force += f_x
                        total_y_force += f_y
                    max_step = max([max_step, abs(total_x_force), abs(total_y_force)])
                    shape01.propigate(total_x_force, total_y_force)
            # Break the propigation loop if the organization stops changing.
            if max_step < 0.01:
                break

    def get_collaborative_evidence(self, sort_list=False):
        """Return a list of evidence/sub-theories that support the opinion.

        Args:
            sort_list (bool, optional): If true, the list will be sorted by points in
                decending order. Defaults to False.

        Returns:
            list: A list of all the collaborative evidence.
        """
        if self.opinion.is_true():
            evidence = self.true_set
        else:
            evidence = self.false_set
        if sort_list:
            output_set = sorted(evidence, key=lambda x: x.total_points(), reverse=True)
            while len(output_set) > 0 and output_set[-1].total_points() < 0.01:
                output_set.pop()
            return output_set
        return evidence

    def get_contradicting_evidence(self, sort_list=False):
        """Return a list of evidence/sub-theories that contradicts the opinion.

        Args:
            sort_list (bool, optional): If true, the list will be sorted by points in
                decending order. Defaults to False.

        Returns:
            list: A list of all the contradicting evidence.
        """
        if self.opinion.is_true():
            evidence = self.false_set
        else:
            evidence = self.true_set
        if sort_list:
            output_set = sorted(evidence, key=lambda x: x.total_points(), reverse=True)
            while len(output_set) > 0 and output_set[-1].total_points() < 0.01:
                output_set.pop()
            return output_set
        return evidence

    def get_controversial_evidence(self, sort_list=False):
        """Return a list of evidence/sub-theories that both support and contradict the opinion.

        Args:
            sort_list (bool, optional): If true, the list will be sorted by points in
                decending order. Defaults to False.

        Returns:
            list: A list of all the controversial evidence.
        """
        if sort_list:
            output_set = sorted(self.intersection_set, key=lambda x: x.total_points(), reverse=True)
            while len(output_set) > 0 and output_set[-1].total_points() < 0.01:
                output_set.pop()
            return output_set
        return self.intersection_set

    def get_unaccounted_evidence(self, sort_list=False):
        """Return a list of evidence/sub-theories that is insignificant to the opinion.

        Args:
            sort_list (bool, optional): If true, the list will be sorted by points in
                decending order. Defaults to False.

        Returns:
            list: A list of all the insignificant evidence.
        """
        if sort_list:
            output_set = sorted(self.outside_set, key=lambda x: x.total_points(), reverse=True)
            while len(output_set) > 0 and output_set[0].total_points() >= 0.01:
                output_set.pop(0)
            return output_set
        return self.outside_set

    def get_svg(self):
        """Output the svg code for diagram.

        Returns:
            str: The svg code for displaying the diagram.
        """
        # Setup
        width = 1200
        r = self.config['radius']
        height = (2.0 * r + self.boarder['top'] + self.boarder['bottom'])
        offset = {
            'x': width / 2 - (self.true_ring.x + self.false_ring.x) / 2,
            'y': self.boarder['top'] + r - self.true_ring.y
        }

        # Construct frame.
        svg = '<center><svg baseProfile="full" version="1.1" viewBox="0 0 %d %d">' % (width, height)
        svg += '<defs><style type="text/css"><![CDATA[.text { font-family: serif; fill: black; }]]>'
        svg += '</style></defs>'

        # Draw hidden elements first to appear below the rest.
        for shape in self.true_shapes + self.intersection_shapes + \
                     self.false_shapes + self.outside_shapes:
            svg += shape.get_highlight_svg(offset=offset)

        # Draw the remaing shapes.
        for shape in [self.true_ring, self.false_ring] + self.true_shapes + \
                     self.intersection_shapes + self.false_shapes + self.outside_shapes:
            svg += shape.get_svg(offset=offset)
        for text in self.text:
            svg += text.get_svg(offset=offset)
        svg += """</svg></center>"""
        return svg

    def get_caption(self):
        """Output caption text for diagram.

        Returns:
            str: The caption text for the diagram.
        """
        text = """The above Venn-Diagram captures the evidence/sub-theories
                   that <b>%s</b> used as shapes. Squares represent evidence and
                   circles represent sub-theories, the size reflects the number
                   of points awarded, and the opacity reflects how factual the
                   evidence/sub-theory is.
                """ % self.opinion.get_owner()
        return text


class OpinionComparisionVennDiagram(OpinionVennDiagram):
    """A class for drawing relative Venn-diagrams (used for comparisons)."""

    def __init__(self, opinion01, opinion02, flat=False, bottom_text=None):
        """Constructor for the OpinionComparisionVennDiagram class.

        Args:
            opinion01 (OpinionNode): The base opinion, used to decide the evidence/sub-theory
                locatoin (the true ring, the false ring, the intersection, or the outside).
            opinion02 (OpinionNode): The comparision opinion, used to decide the size and colour
                of each shape.
            flat (bool, optional): If true, the sub-theories are flattend. Defaults to False.
            bottom_text ([type], optional): Mainly used for debug statements. Defaults to None.

        Returns:
            [type]: [description]
        """
        self.opinion01 = opinion01
        self.opinion02 = opinion02
        super().__init__(opinion01, flat, bottom_text)

    def calc_membership(self):
        """Group opinion nodes into: true, false, true & false, and neither."""
        # Setup
        self.true_set = []
        self.intersection_set = []
        self.false_set = []
        self.outside_set = []

        # Construct a list of nodes.
        theory = self.opinion01.content
        if self.flat:
            nodes = theory.get_flat_nodes()
            get_node01 = self.opinion01.get_flat_node
            get_node02 = self.opinion02.get_flat_node
        else:
            nodes = theory.get_nodes()
            get_node01 = self.opinion01.get_node
            get_node02 = self.opinion02.get_node

        # Populate the sets (create dummy nodes to customize weight and colour).
        for node in nodes:

            # Get or create node01
            points_node01 = get_node01(content=node)
            if points_node01 is None:
                points_node01 = NodePointerBase.create(
                    parent=self.opinion01,
                    content=node,
                    true_points=0.0,
                    false_points=0.0,
                )
            # Get or create node02
            points_node02 = get_node02(content=node)
            if points_node02 is None:
                points_node02 = NodePointerBase.create(
                    parent=self.opinion02,
                    content=node,
                    true_points=0.0,
                    false_points=0.0,
                )

            # Assign nodes to sets
            if points_node01.total_points() < 0.01:
                if points_node02.total_points() > 0:
                    self.outside_set.append(points_node02)
            elif points_node01.true_ratio() >= 0.66:
                if points_node02.total_points() > 0:
                    self.true_set.append(points_node02)
            elif points_node01.false_ratio() >= 0.66:
                if points_node02.total_points() > 0:
                    self.false_set.append(points_node02)
            else:
                if points_node02.total_points() > 0:
                    self.intersection_set.append(points_node02)

    def get_caption(self):
        """Output caption text for diagram.

        Returns:
            str: The caption text for the diagram.
        """
        text = """The above Venn-Diagram captures the evidence/sub-theories
                   that <b>%s</b> used to construct their opinion. The size,
                   colour, and opacity reflect the belief of <b>%s's</b> opinion.
                """ % (self.opinion01.get_owner(), self.opinion02.get_owner())
        return text


class DemoVennDiagram(OpinionVennDiagram):
    """A class for drawing demo Venn-diagrams (fake data)."""

    def __init__(self,
                 true_set_size=10,
                 intersection_set_size=10,
                 false_set_size=10,
                 outside_set_size=10):
        """The constructor for the DemoVennDiagram class.

        Args:
            true_set_size (int, optional): The number of random true OpinionNodes to be generated.
                Defaults to 10.
            intersection_set_size (int, optional): [description]. Defaults to 10.
            false_set_size (int, optional): [description]. Defaults to 10.
            outside_set_size (int, optional): [description]. Defaults to 10.
        """
        random.seed()
        seed = random.randint(0, 100)
        random.seed(seed)

        opinion = get_demo_opinion()
        theory = opinion.content
        content_nodes = theory.get_nodes()

        opinion.saved_true_points = opinion.true_points()
        opinion.saved_false_points = opinion.false_points()

        total_true_points = 0
        total_false_points = 0
        opinion.saved_nodes = []

        for i in range(random.randint(1, true_set_size)):
            new_node = NodePointerBase.create(
                parent=opinion,
                content=random.choice(content_nodes),
                true_points=random.randint(1, 100),
                false_points=random.randint(1, 10),
            )
            opinion.saved_nodes.append(new_node)
            total_true_points += new_node.true_points()
            total_false_points += new_node.false_points()

        for i in range(random.randint(1, intersection_set_size)):
            new_node = NodePointerBase.create(
                parent=opinion,
                content=random.choice(content_nodes),
                true_points=random.randint(1, 10),
                false_points=random.randint(1, 10),
            )
            opinion.saved_nodes.append(new_node)
            total_true_points += new_node.true_points()
            total_false_points += new_node.false_points()

        for i in range(random.randint(1, false_set_size)):
            new_node = NodePointerBase.create(
                parent=opinion,
                content=random.choice(content_nodes),
                true_points=random.randint(1, 10),
                false_points=random.randint(1, 100),
            )
            opinion.saved_nodes.append(new_node)
            total_true_points += new_node.true_points()
            total_false_points += new_node.false_points()

        for i in range(random.randint(1, outside_set_size)):
            new_node = NodePointerBase.create(
                parent=opinion,
                content=random.choice(content_nodes),
                true_points=random.randint(1, 5),
                false_points=random.randint(1, 5),
            )
            opinion.saved_nodes.append(new_node)
            total_true_points += new_node.true_points()
            total_false_points += new_node.false_points()

        # normalize points to create the weights
        for node in opinion.saved_nodes:
            if total_true_points > 0:
                node.saved_true_points = (node.true_points() /
                                          total_true_points) * opinion.true_points()
            else:
                node.saved_true_points = 0.0
            if total_false_points > 0:
                node.saved_false_points = (node.false_points() /
                                           total_false_points) * opinion.false_points()
            else:
                node.saved_false_points = 0.0

        super().__init__(opinion, bottom_text=str(seed))

    def get_caption(self):
        """Dummy method, there is no caption text for this diagram.

        Returns:
            str: Blank
        """
        return ''


# *******************************************************************************
# main (used for testing)
# *******************************************************************************
if __name__ == "__main__":
    pass
