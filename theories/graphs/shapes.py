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


# *******************************************************************************
# Defines
# *******************************************************************************
class Colour():
    """A class for colour constants."""
    RED = '#FF0000'
    BLACK = '#000000'
    PINK = '#FF8080'
    GREY = '#808080'
    BLACK_AND_RED = 'B&R'
    NONE = 'none'

    def get_transparent_colour(colour):
        """Converts a dark colour to a light colour.

        Args:
            colour (Colour): The input colour.

        Returns:
            Colour: The lighter version of the input colour.
        """
        if colour == Colour.RED:
            return Colour.PINK
        if colour == Colour.BLACK:
            return Colour.GREY
        assert False

    def get_red_black_mix(red_percent):
        if isinstance(red_percent, int) and 0 <= red_percent and red_percent <= 100:
            red_mix = 1.0 * red_percent / 100
        assert isinstance(red_percent, float) and 0.0 <= red_percent and red_percent <= 1.0

        red_mix = int(0xff * red_percent)
        print('#' + hex(red_mix)[2:] + '0000')
        return '#' + hex(red_mix)[2:] + '0000'



# *******************************************************************************
# Methods
#
#
#
#
#
#
# *******************************************************************************
def offset_xy(x, y, offset):
    """Helper method for offseting x and y using a dictionary.

    Args:
        x (float): The x coordiante to offset.
        y (float): The y coordiante to offset.
        offset (dict('x':float, 'y':float), optional): The x,y offset dict to be used.

    Returns:
        tuple(float, float): A tuple of the offset x,y.
    """
    if isinstance(offset, dict):
        if 'x' in offset:
            x += offset['x']
        if 'y' in offset:
            y += offset['y']
    return x, y


# *******************************************************************************
# Drawing classes
#
#
#
#
#
#
# *******************************************************************************


class ShapeBase():
    """Base class for all shapes."""

    def __init__(self, colour=Colour.BLACK, stroke_colour=Colour.BLACK, stroke_width=2.0):
        """The constructor for ShapeBase class.

        Args:
            colour ([type], optional): [description]. Defaults to Colour.BLACK.
            stroke_colour ([type], optional): [description]. Defaults to Colour.BLACK.
            stroke_width (float, optional): The stroke width for the rectangle. Defaults to 2.0.
        """
        self.colour = colour
        self.stroke_colour = stroke_colour
        self.stroke_width = stroke_width

    def get_svg(self, offset=None):
        """Output the svg code for the shape object.

        Args:
            offset (dict('x':float, 'y':float), optional): The x,y offset dict to be used.
                Defaults to None.

        Returns:
            str: The svg code for displaying the shape.
        """


class Text(ShapeBase):
    """A class for drawing text."""

    def __init__(self, text, x, y, size=30, align='middle', bold=False, colour=None):
        """The constructor for the Text class.

        Args:
            text (str): The text to display.
            x (float): The x coordinate of the text.
            y (float): The y coordinate of the text.
            size (int, optional): The font size. Defaults to 30.
            align (str, optional): How to align the text (to be parsed by svg).Defaults to
                'middle'.
            bold (bool, optional): If true, the text will be dispalyed as bold. Defaults to False.
            colour (Colour, optional): The fill colour for the text. Defaults to None.
        """
        self.text = text
        self.x = x
        self.y = y
        self.size = size
        self.bold = bold
        self.align = align
        super().__init__(colour)

    def get_svg(self, offset=None):
        """Output the svg code for the text object.

        Args:
            offset (dict('x':float, 'y':float), optional): The x,y offset dict to be used.
                Defaults to None.

        Returns:
            str: The svg code for displaying the text.
        """
        x, y = offset_xy(self.x, self.y, offset)
        svg = '<text text-anchor="%s" x="%d" y="%d"' % (self.align, x, y)
        svg += ' font-size="%d" font-family="FreeSerif"' % self.size
        if self.bold:
            svg += ' font-weight="bold"'
        if self.colour is not None:
            svg += ' fill="%s"' % self.colour
        svg += '>%s</text>' % self.text
        return svg


class Circle(ShapeBase):
    """A class for drawing circles."""

    def __init__(self, x, y, r, stroke_width=2.0, colour=Colour.BLACK):
        """The constructor for the Circle class.

        Args:
            x (float): The x coordinate of the circle.
            y (float): The y coordinate of the circle.
            r (float): The radius of the circle.
            colour (Colour, optional): The fill colour for the circle. Defaults to Colour.BLACK.
        """
        self.x = x
        self.y = y
        self.r = r
        super().__init__(stroke_width=stroke_width, colour=colour)

    def get_svg(self, offset=None):
        """Output the svg code for the circle object.

        Args:
            offset (dict('x':float, 'y':float), optional): The x,y offset dict to be used.
                Defaults to None.

        Returns:
            str: The svg code for displaying the circle.
        """
        x, y = offset_xy(self.x, self.y, offset)
        svg = '<circle cx="%d" cy="%d" r="%d" fill="%s"' % (x, y, self.r, self.colour)
        svg += ' stroke="black" stroke-width="%0.2f"/>' % self.stroke_width
        return svg


class Rectangle(ShapeBase):
    """A class for drawing rectangles."""

    def __init__(self,
                 x01,
                 y01,
                 x02,
                 y02,
                 colour=Colour.NONE,
                 stroke_colour=Colour.BLACK,
                 stroke_width=2.0,
                 hatch=False):
        """The constructor for the Rectangle class.

        Args:
            x01 (float): The bottom left x coordinate of the rectangle.
            y01 (float): The bottom left y coordinate of the rectangle.
            x02 (float): The top right x coordinate of the rectangle.
            y02 (float): The top right y coordinate of the rectangle.
            colour (Colour, optional): The fill colour for the rectangle. Defaults to Colour.NONE.
            stroke_colour (Colour, optional): The stroke colour for the rectangle. Defaults to
                Colour.BLACK.
            stroke_width (float, optional): The stroke width for the rectangle. Defaults to 2.0.
            hatch (bool, optional): If true, the fill will be hatched. Defaults to False.
        """
        if x02 > x01:
            self.x01 = x01
            self.x02 = x02
        else:
            self.x01 = x02
            self.x02 = x01
        if y02 > y01:
            self.y01 = y01
            self.y02 = y02
        else:
            self.y01 = y02
            self.y02 = y01
        self.hatch = hatch
        super().__init__(colour, stroke_colour, stroke_width)

    def get_svg(self, offset=None):
        """Output the svg code for the rectangle object.

        Args:
            offset (dict('x':float, 'y':float), optional): The x,y offset dict to be used.
                Defaults to None.

        Returns:
            str: The svg code for displaying the rectangle.
        """
        x01, y01 = offset_xy(self.x01, self.y01, offset)
        x02, y02 = offset_xy(self.x02, self.y02, offset)
        svg = '<rect x="%d" y="%d" width="%d" height="%d"' % (x01, y01, x02 - x01, y02 - y01)
        if self.hatch:
            svg += ' style="fill: url(#hatch)"'
        else:
            svg += ' fill="%s"' % self.colour
        svg += ' stroke="%s" stroke-width="%0.2f"/>' % (self.stroke_colour, self.stroke_width)
        return svg


class Wedge(ShapeBase):
    """A class for drawing wedges (used for the pie-charts)."""

    def __init__(self,
                 x,
                 y,
                 theta01,
                 theta02,
                 radius=100,
                 c_offset=0.0,
                 explode=0.0,
                 stroke_width=2.0,
                 colour=Colour.BLACK):
        """The constructor for the Wedge class.

        Args:
            x (float): The x coordinate of the wedge (arc center).
            y (float): The y coordinate of the wedge (arc center).
            theta01 (float, deg): One of the angles for the wedge (theta01 < theta02).
            theta02 (float, deg): One of the angles for the wedge (theta01 < theta02).
            radius (int, optional): The arc radius for the wedge. Defaults to 100.
            c_offset (float, optional): The distance to offset wedge center (point).
                Defaults to 0.0.
            explode (float, optional): The distance to push the wedge away from center.
                Defaults to 0.0.
            colour (Colour, optional): The fill colour for the wedge. Defaults to Colour.BLACK.
        """
        self.x = x
        self.y = y
        self.theta01 = theta01
        self.theta02 = theta02
        self.radius = radius
        self.c_offset = c_offset
        self.explode = explode
        super().__init__(stroke_width=stroke_width, colour=colour)

    def get_svg(self, offset=None):
        """Output the svg code for the wedge object.

        Args:
            offset (dict('x':float, 'y':float), optional): The x,y offset dict to be used.
                Defaults to None.

        Returns:
            str: The svg code for displaying the wedge.
        """
        r = self.radius
        theta01 = math.radians(self.theta01)
        theta02 = math.radians(self.theta02)
        dt = (theta02 + theta01) / 2
        large_arc_flag = int(self.theta02 - self.theta01 > 180)

        dx00, dy00 = offset_xy(self.x, self.y, offset)

        x01 = 1.0 * r * math.cos(theta01)
        y01 = 1.0 * r * math.sin(theta01)
        x02 = 1.0 * r * math.cos(theta02)
        y02 = 1.0 * r * math.sin(theta02)

        dr01 = self.explode
        dx01, dy01 = offset_xy(1.0 * dr01 * math.cos(dt), 1.0 * dr01 * math.sin(dt), offset)

        dr02 = self.c_offset
        dx02, dy02 = offset_xy(1.0 * dr02 * math.cos(dt), 1.0 * dr02 * math.sin(dt), offset)

        svg = '<path fill="%s" stroke="black" stroke-width="%0.2f"' % (self.colour,
                                                                       self.stroke_width)
        svg += ' d="M %0.2f,%0.2f' % (dx00 + dx01 + dx02, dy00 + dy01 + dy02)
        svg += ' L %0.2f,%0.2f' % (x01 + dx00 + dx01, y01 + dy00 + dy01)
        svg += ' A %0.2f,%0.2f 0 %d 1 %0.2f,%0.2f' % (r, r, large_arc_flag, x02 + dx00 + dx01,
                                                      y02 + dy00 + dy01)
        svg += ' L %0.2f,%0.2f Z"/>' % (dx00 + dx01 + dx02, dy00 + dy01 + dy02)
        return svg


class Polygon(ShapeBase):
    """A class for drawing polygons."""

    def __init__(self, path, stroke_width=2.0, colour=Colour.BLACK):
        """The constructor for the Polygon class.

        Args:
            path (list(tuple(float,float))): A list of x,y points.
            colour ([type], optional): The fill colour for the polygon. Defaults to Colour.BLACK.
        """
        self.path = path
        super().__init__(stroke_width=stroke_width, colour=colour)

    def get_svg(self, offset=None):
        """Output the svg code for the polygon object.

        Useful references:
            https://bocoup.com/blog/using-svg-patterns-as-fills
            https://hackernoon.com/a-simple-pie-chart-in-svg-dbdd653b6936

        Args:
            offset (dict('x':float, 'y':float), optional): The x,y offset dict to be used.
                Defaults to None.

        Returns:
            str: The svg code for displaying the polygon.
        """
        svg = '<path fill="%s" stroke="black" stroke-width="%0.2f"' % (self.colour,
                                                                       self.stroke_width)
        svg += ' d="'
        for i, (x, y) in enumerate(self.path):
            if i == 0:
                svg += 'M'
            else:
                svg += ' L'
            x, y = offset_xy(x, y, offset)
            svg += ' %0.2f,%0.2f' % (x, y)
        svg += ' Z"/>'
        return svg


class Arrow(ShapeBase):
    """A class for drawing arrows (currently only horizontal)."""

    def __init__(self, x01, y01, x02, y02, stroke_width=2.5, colour=Colour.BLACK):
        """The constructor for the Polygon class.

        Args:
            x01 (float): The x coordinate for the base of the arrow.
            y01 (float): The y coordinate for the base of the arrow.
            x02 (float): The x coordinate for the tip of the arrow.
            y02 (float): The y coordinate for the tip of the arrow.
            stroke_width (float, optional): The stroke width of the arrow (the rest of the arrow
                is proportionally scaled). Defaults to 2.5.
            colour (Colour, optional): The arrow colour. Defaults to Colour.BLACK.
        """
        self.x01 = x01
        self.x02 = x02
        self.y01 = y01
        self.y02 = y02
        super().__init__(colour, stroke_width=stroke_width)

    def get_svg(self, offset=None):
        """Output the svg code for the arrow object.

        Args:
            offset (dict('x':float, 'y':float), optional): The x,y offset dict to be used.
                Defaults to None.

        Returns:
            str: The svg code for displaying the arrow.
        """
        x01, y01 = offset_xy(self.x01, self.y01, offset)
        x02, y02 = offset_xy(self.x02, self.y02, offset)
        h = self.stroke_width * 3

        svg = '<path fill="none" stroke="%s"' % self.colour
        svg += ' stroke-width="%0.2f"' % self.stroke_width
        svg += ' d="M %0.2f,%0.2f' % (x01, y01)
        svg += ' L %0.2f,%0.2f' % (x01, y01)
        if x02 > x01:
            svg += ' L %0.2f,%0.2f Z"/>' % (x02 - h, y02)
            svg += '<path fill="%s" stroke="none"' % (self.colour)
            svg += ' d=M %0.2f,%0.2f' % (x02 - 2 * h, y02 - h)
            svg += ' Q %0.2f,%0.2f,%0.2f,%02.f' % (x02 - h, y02, x02 - 2 * h, y02 + h)
            svg += ' L %0.2f,%0.2f' % (x02, y02)
        else:
            svg += ' L %0.2f,%0.2f Z"/>' % (x02 + h, y02)
            svg += '<path fill="%s" stroke="none"' % (self.colour)
            svg += ' d=M %0.2f,%0.2f' % (x02 + 2 * h, y02 - h)
            svg += ' Q %0.2f,%0.2f,%0.2f,%02.f' % (x02 + h, y02, x02 + 2 * h, y02 + h)
            svg += ' L %0.2f,%0.2f' % (x02, y02)
        svg += ' Z"/>'
        return svg


class Group(ShapeBase):
    """A class for grouping svg objects with optional hide tag."""

    def __init__(self, tag_id='', hidden=False):
        """The constructor for the Group class.

        Args:
            tag_id (str, optional): Used for hidding/unhiding the objects in the group.
                Defaults to ''.
            hidden (bool, optional): If true, the objects in the group will be hidden by default.
                Defaults to False.
        """
        self.tag_id = tag_id
        self.hidden = hidden
        self.shapes = []
        super().__init__()

    def add(self, shape):
        """Add a shape to group.

        Args:
            shape (ShapeBase): The object to add to the group.
        """
        self.shapes.append(shape)

    def get_svg(self, offset=None):
        """Output the svg code for the group object.

        Returns:
            str: The svg code for displaying the group.
        """
        if self.hidden:
            svg = '<g id="%s" visibility="hidden">' % self.tag_id
        else:
            svg = '<g id="%s">' % self.tag_id
        for shape in self.shapes:
            svg += shape.get_svg(offset)
        svg += '</g>'
        return svg


# *******************************************************************************
# main (used for testing)
# *******************************************************************************
if __name__ == "__main__":
    pass
