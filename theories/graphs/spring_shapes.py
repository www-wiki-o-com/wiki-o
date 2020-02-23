"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       theories/graphs/spring_shapes.py
@brief      A collection of self organizing shapes
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# Imports
# *******************************************************************************
import enum
import math
from math import pi as PI

from theories.graphs.shapes import Colour, ShapeBase
from theories.graphs.shapes import offset_xy


# *******************************************************************************
# Defines
# *******************************************************************************
class Direction(enum.Enum):
    """Enum for direction to shapes."""
    IN = 1
    OUT = 2


# *******************************************************************************
# Self organizing shapes
#
#
#
#
#
#
# *******************************************************************************


class SpringShapeBase(ShapeBase):
    """The parent class for self organizaing shapes (SpringShapeBase).

    These shapes are mainly used in Venn-diagrams. All shapes are treated as circles (squares
    will fit inside a circle). The spring aspect allows the shapes to repel each other and thus
    avoid overlap.

    Usage:
      - Calculate the total force on a shape imposed from all the other spring shapes.
      - Use the total force to move (propigate) the shape into a location with lower potential.

    Attributes:
        x (float): The initial x coordinate.
        y (float): The initial y coordinate.
        r (float): The bounding radius (w.r.t the spring force all shapes are treated
            as circles).
        colour (Colour, optional): The shape's fill colour. Defaults to Colour.BLACK.
        stroke_colour (Colour, optional): The shape's line colour. Defaults to Colour.BLACK.
        spring_length (float): The length of the virtual spring.
        spring_constant (float): The spring constant for the virtual spring.
        DEFAULT_SPRING_LENGTH (float): The default value of spring_length.
        DEFAULT_SPRING_CONSTANT (float): The default value of spring_constant.
    """
    # Constants
    DEFAULT_SPRING_LENGTH = 5.0
    DEFAULT_SPRING_CONSTANT = 1.0

    def __init__(self, x, y, r, colour=Colour.BLACK, stroke_colour=Colour.BLACK, stroke_width=2.0):
        """The constructor for the SpringShapeBase class.

        Args:
            x (float): The initial x coordinate.
            y (float): The initial y coordinate.
            r (float): The bounding radius (w.r.t the spring force all shapes are treated
                as circles).
            colour (Colour, optional): The shape's fill colour. Defaults to Colour.BLACK.
            stroke_colour (Colour, optional): The shape's line colour. Defaults to Colour.BLACK.
        """
        self.x = x
        self.y = y
        self.r = r
        self.spring_length = self.DEFAULT_SPRING_LENGTH
        self.spring_constant = self.DEFAULT_SPRING_CONSTANT
        super().__init__(colour=colour, stroke_colour=stroke_colour, stroke_width=stroke_width)

    def __str__(self):
        """Output debug text for diagram.

        Returns:
            str: Text that captures the shape coordinates.
        """
        return "(%0.3f, %0.3f, %0.3f)" % (self.x, self.y, self.r)

    def get_separation_vector(self, shape02, direction=Direction.OUT):
        """Calculate the separation vector from self to shape02.

        Args:
            shape02 (SpringShapeBase): The other shape.
            direction (Direction, optional): Two solid objects will force other shapes "outwards",
                while hollow objects, such as rings, will push them "inwards". Defaults to
                Direction.OUT.

        Returns:
            tuple(float, float, float): The direction vector (x, y, magnitude) relative to self.
                Negative magnitude indicates that the shapes are in collision.
        """
        dx = shape02.x - self.x
        dy = shape02.y - self.y
        d = math.sqrt(dx**2 + dy**2)
        unit_x = 1.0 * dx/d
        unit_y = 1.0 * dy/d
        if direction == Direction.OUT:
            separation = d - self.r - shape02.r
            return unit_x, unit_y, separation
        else:
            assert isinstance(self, Ring) or isinstance(shape02, Ring)
            if isinstance(self, Ring):
                separation = self.r - (d + shape02.r)
            else:
                separation = shape02.r - (d + self.r)
            return -unit_x, -unit_y, separation

    def get_spring_force(self, shape02, direction=Direction.OUT):
        """Calculates the force imposed on shape02 by self.

        Args:
            shape02 (SpringShapeBase): The other shape.
            direction (Direction, optional): The direction of the force (IN or OUT). Defaults
                to Direction.OUT.

        Returns:
            tuple(float, float): The force vector (x,y) relative to self.
        """
        unit_x, unit_y, separation = self.get_separation_vector(shape02, direction)
        compression = max(0, self.spring_length - separation)
        force = 1.0 * self.spring_constant * compression
        return force * unit_x, force * unit_y

    def reset_spring_constant(self):
        """Resets the spring constant.

        The spring force constant degrades over each iteration, this method resets the spring
        force constant.
        """
        self.spring_constant = self.DEFAULT_SPRING_CONSTANT

    def propigate(self, dx, dy):
        """A method for calculating the step distance based on the repel force.

        Args:
            dx (float): The x distance to propigate the shape.
            dy (float): The y distance to propigate the shape.
        """
        self.x += dx
        self.y += dy


class EvidenceShape(SpringShapeBase):
    """A sub-class of spring shape for square objects (evidence)."""

    def __init__(self, node, x, y, area):
        """Constructor for the EvidenceShape.

        The bounding radius is setup to encompase the square and is used for the spring force logic.

        Args:
            node (OpinionNode): [description]
            x (float): The initial x coordinate.
            y (float): The initial y coordinate.
            area (float): The area of the square.
        """
        self.node = node
        self.length = math.sqrt(area)
        bounding_radius = (self.length/2) * math.sqrt(2)
        super().__init__(x, y, bounding_radius)

    def get_highlight_svg(self, offset=None):
        """Output the svg code for the hidden-highlight shape.

        This graphic is hidden by default but is revealed to highlight the shape.

        Args:
            offset (dict('x':float, 'y':float), optional): The x,y offset dict to be used.
                Defaults to None.

        Returns:
            str: The svg code for displaying the shape.
        """
        length = self.length + 15
        x = self.x - length/2
        y = self.y - length/2
        x, y = offset_xy(x, y, offset)
        svg = '<rect id="%s" visibility="hidden"' % self.node.tag_id()
        svg += ' x="%d" y="%d" ' % (x, y)
        svg += ' width="%d" height="%d" ' % (length, length)
        svg += ' fill="none" stroke="lime" stroke-width="10"/>'
        return svg

    def get_svg(self, offset=None):
        """Output the svg code for the shape (shade is a function of fact/intuition).

        The colour and shade are calculated based on:
            - How the node is being used in the theory, red for false, black for true,
            - The colour is transparent if the evidence is non-factual.

        Args:
            offset (dict('x':float, 'y':float), optional): The x,y offset dict to be used.
                Defaults to None.

        Returns:
            str: The svg code for displaying the shape.
        """
        if self.node.true_points() >= self.node.false_points():
            if self.node.is_verifiable():
                colour = Colour.BLACK
            else:
                colour = Colour.GREY
        else:
            if self.node.is_verifiable():
                colour = Colour.RED
            else:
                colour = Colour.PINK
        length = self.length
        x = self.x - length/2
        y = self.y - length/2
        x, y = offset_xy(x, y, offset)
        svg = '<a target="_blank" xlink:href="%s" target="_blank">' % self.node.theory_node.url()
        svg += '<rect x="%d" y="%d"' % (x, y)
        svg += ' width="%d" height="%d"' % (length, length)
        svg += ' fill="%s" stroke-width="0">' % colour
        svg += '<title>%s</title>' % str(self.node)
        svg += '</rect></a>'
        return svg


class SubtheoryShape(SpringShapeBase):
    """A sub-class of spring shape for circle objects (sub-theories)."""

    def __init__(self, node, x, y, area):
        """The constructor for the SubTheoryShape class.

        Args:
            node (OpinionNode): The sub-theory node (used for colour and captions).
            x (float): The initial x coordinate.
            y (float): The initial y coordinate.
            area (float): The area of the circle.
        """
        self.node = node
        bounding_radius = math.sqrt(area/PI)
        super().__init__(x, y, bounding_radius)

    def get_highlight_svg(self, offset=None):
        """Output the svg code for the hidden-highlight shape.

        This graphic is hidden by default but is revealed to highlight the shape.

        Args:
            offset (dict('x':float, 'y':float), optional): The x,y offset dict to be used.
                Defaults to None.

        Returns:
            str: The svg code for displaying the shape.
        """
        x = self.x
        y = self.y
        x, y = offset_xy(x, y, offset)
        r = self.r + 7.5
        svg = '<circle id="%s" visibility="hidden"' % self.node.tag_id()
        svg += ' cx="%d" cy="%d" r="%d"' % (x, y, r)
        svg += ' fill="none" stroke="lime" stroke-width="10"/>'
        return svg

    def get_svg(self, offset=None):
        """Output the svg code for the shape (opacity is a function of fact/intuition).

        The colour and opacity are calculated based on:
            - how the node is being used in the theory, red for false, black for true,
            - currently the colour is never transparent.

        Args:
            offset (dict('x':float, 'y':float), optional): The x,y offset dict to be used.
                Defaults to None.

        Returns:
            str: The svg code for displaying the shape.
        """
        x = self.x
        y = self.y
        x, y = offset_xy(x, y, offset)
        r = self.r
        if self.node.true_points() >= self.node.false_points():
            colour = Colour.BLACK
        else:
            colour = Colour.RED
        svg = '<a target="_blank" xlink:href="%s" target="_blank">' % self.node.theory_node.url()
        svg += '<circle'
        svg += ' cx="%d" cy="%d" r="%d"' % (x, y, r)
        svg += ' fill="%s" stroke-width="0">' % colour
        svg += '<title>%s</title>' % str(self.node)
        svg += '</circle></a>'
        return svg


class Ring(SpringShapeBase):
    """A ring shape, mainly used for the true and false sets in the Venn diagram."""

    # Constants
    DEFAULT_SPRING_LENGTH = 10
    DEFAULT_SPRING_CONSTANT = 1.0

    def __init__(self, x, y, r, colour=Colour.NONE, stroke_colour=Colour.BLACK,
                 x_min=None, x_max=None):
        """The constructor for the Ring class.

        Rings will not propigate in the y direction or outside their x boundaries.

        Args:
            x (float): The initial x coordinate.
            y (float): The initial y coordinate.
            r (float): The radius of the ring.
            colour (Colour, optional): The fill colour. Defaults to Colour.NONE.
            stroke_colour (Colour, optional): The stroke colour. Defaults to Colour.BLACK.
            x_min (float, optional): The minimum x possition the ring may obtain. Defaults to None.
            x_max (float, optional): The maximum x possition the ring may obtain. Defaults to None.
        """
        self.x_min = x_min
        self.x_max = x_max
        super().__init__(x, y, r, colour=colour, stroke_colour=stroke_colour)

    def propigate(self, dx, dy):
        """Move the ring by dx,dy.

        Args:
            dx (float): The x distance to move the ring.
            dy (float): The x distance to move the ring.
        """
        self.x += dx
        if self.x_min is not None:
            self.x = max(self.x, self.x_min)
        if self.x_max is not None:
            self.x = min(self.x, self.x_max)

    def get_svg(self, offset=None):
        """Output the svg code for the shape.

        Args:
            offset (dict('x':float, 'y':float), optional): The x,y offset dict to be used.
                Defaults to None.

        Returns:
            str: The svg code for displaying the shape.
        """
        x = self.x
        y = self.y
        x, y = offset_xy(x, y, offset)
        r = self.r
        svg = """<circle cx="%d" cy="%d" r="%d" fill="%s" stroke="%s" stroke-width="4"/>
              """ % (x, y, r, self.colour, self.stroke_colour)
        return svg


class Wall(SpringShapeBase):
    """A boundary that repels shapes to prevent them from leaving the frame of view."""

    def __init__(self, x, y):
        """Constructor for the Wall class.

        Walls only have one coordinate, x or y, if x, then the wall extends the entire y axis.

        Args:
            x (float or None): The x coordinate of the wall (must be float if y is None).
            y (float or None): The x coordinate of the wall (must be float if x is None).
        """
        assert x is None or y is None
        super().__init__(x, y, 0)

    def get_separation_vector(self, shape02, direction=Direction.IN):
        """Calculate distance to boundary.

        Walls are a special SpringShape that repel only in one direction (x or y). If the direction
            is x and the possition of the wall below the axis (negative), then the wall's force is
            always upwards.

        Args:
            shape02 (SpringShapeBase): The other shape.
            direction (Direction, optional): Two solid objects will force other shapes "outwards",
                while hollow objects, such as rings, will push them "inwards". Defaults to
                Direction.IN.

        Returns:
            tuple(float, float, float): The direction vector (x, y, magnitude) relative to self.
                Negative magnitude indicates that the shapes are in collision.
        """
        assert direction == Direction.IN
        assert self.x is not None or self.y is not None
        unit_x = unit_y = 0.0
        if self.x is not None:
            if self.x < 0:
                unit_x = 1.0
                separation = shape02.x - shape02.r - self.x
            else:
                unit_x = -1.0
                separation = self.x - shape02.x - shape02.r
        elif self.y is not None:
            if self.y < 0:
                unit_y = 1.0
                separation = shape02.y - shape02.r - self.y
            else:
                unit_y = -1.0
                separation = self.y - shape02.y - shape02.r
        return unit_x, unit_y, separation

    def propigate(self, dx, dy):
        """Dummy method, walls don't move."""
        assert False

    def get_svg(self, offset=None):
        """Dummy method, this shape has nothing to display."""
        assert False


# *******************************************************************************
# main (used for testing)
# *******************************************************************************
if __name__ == "__main__":
    pass
