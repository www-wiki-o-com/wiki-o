"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       theories/graphs.py
@brief      A collection of classes/methods for creating, viewing, and manipulating graphs
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# imports
# *******************************************************************************
import sys
import math
import numpy
import random

from math import pi as PI
from django.urls import reverse
from django.contrib.staticfiles.templatetags.staticfiles import static

from .models import TheoryNode, NodePointerBase
from . import models


# *******************************************************************************
# methods
#
#
#
#
#
#
# *******************************************************************************


# *******************************************************************************
# Self organizing shapes
#
#
#
#
#
#
# *******************************************************************************


# ************************************************************
# Class constants:
# B: boundary or length of spring
# K: spring force constant. A value of one indicates a repelled shape overlapping a shape by dx, will move a distance of dx.
# ************************************************************
class SpringShape:
    """A parent class for shapes used for the Venn-diagram. All shapes are
       treated as circles (squares will fit inside a circle). The spring aspect
       allows the shapes to repel each other and thus avoid overlap."""

    # defines
    B = 5.0
    K = 1.0

    # ******************************
    #
    # ******************************
    def __init__(self, x, y, r, colour='black', stroke_colour='black', opacity=1.0):
        """A spring shape is defined by its coordinates, encapsulating radius, colour, and opacity."""
        self.r = r
        self.x = x
        self.y = y
        self.k = self.K
        self.colour = colour
        self.opacity = opacity
        self.stroke_colour = stroke_colour

    # ******************************
    #
    # ******************************
    def __str__(self):
        """Output coordinates for debug information."""
        return "(%0.3f, %0.3f, %0.3f)" % (self.x, self.y, self.r)

    # ******************************
    #
    # ******************************
    def out_dist(self, object02):
        """Calculate distance to object02 assuming the spring is on the outside of the shape."""
        dx = self.x - object02.x
        dy = self.y - object02.y
        d = math.sqrt(dx**2 + dy**2)
        ud = d - self.r - object02.r
        ux = 1.0*dx/d
        uy = 1.0*dy/d
        return ux, uy, ud

    # ******************************
    #
    # ******************************
    def in_dist(self, object02):
        """Calculate distance to object02 assuming the spring is on the inside of the shape."""
        dx = object02.x - self.x
        dy = object02.y - self.y
        d = math.sqrt(dx**2 + dy**2)
        if isinstance(self, Ring):
            ud = self.r - (d + object02.r)
        else:
            ud = object02.r - (d + self.r)
            assert isinstance(object02, Ring)
        ux = 1.0*dx/d
        uy = 1.0*dy/d
        return ux, uy, ud

    # ******************************
    # try k = 0.1
    # ******************************
    def inverse_force(self, object02):
        """A force method based on inverse distance (not used)."""
        k = object02.k
        B = object02.B
        if direction == 'out':
            ux, uy, ud = object02.out_dist(self)
        elif direction == 'in':
            ux, uy, ud = object02.in_dist(self)
        d = max(0.01, ud)
        f = -min(0.1, 1.0 * k * (max(0.3, object02.r)/d)**10)
        return f*ux, f*uy

    # ******************************
    #
    # ******************************
    def spring_force(self, object02, direction='out'):
        """A force method based linear distance with option to flip direction."""
        k = object02.k
        B = object02.B
        if direction == 'out':
            ux, uy, ud = object02.out_dist(self)
        elif direction == 'in':
            ux, uy, ud = object02.in_dist(self)
        f = -1.0 * k * max(0, B - ud)
        return f*ux, f*uy

    # ******************************
    #
    # ******************************
    def reset_k(self):
        """The spring force degrades over each iteration, this method resets the
           spring force constant."""
        self.k = self.K

    # ******************************
    #
    # ******************************
    def get_force(self, object02, direction='out'):
        """A pass-through method for calculating the repel force."""
        return self.spring_force(object02, direction=direction)

    # ******************************
    #
    # ******************************
    def propigate(self, dx, dy):
        """A method for calculating the step distance based on the repel force."""
        self.x += dx
        self.y += dy


# ************************************************************
#
# ************************************************************
class EvidenceShape(SpringShape):
    """A sub-class of spring shape for square objects (evidence)."""

    # ******************************
    #
    # ******************************
    def __init__(self, node, x, y, area, colour='black', opacity=1.0):
        """Setup the repel radius for avoiding overlap."""
        self.node = node
        self.l = math.sqrt(area)           # a = l x w
        # special relation for 45deg triangles
        r = (self.l/2) * math.sqrt(2)
        super().__init__(x, y, r, colour, opacity)

    # ******************************
    # <g transform="rotate(0,%d,%d)"></g>
    # ******************************
    def svg_hidden(self, offset={'x': 0, 'y': 0}):
        """Output the svg code for the hidden-highlight shape."""
        l = self.l + 15
        x = self.x - l/2
        y = self.y - l/2
        svg = """<rect id="%s" visibility="hidden" x="%d" y="%d" width="%d" height="%d" fill="none" stroke="lime" stroke-width="10"/>
              """ % (
            self.node.tag_id(),
            offset['x'] + x,
            offset['y'] + y,
            l,
            l,
        )
        return svg

    # ******************************
    # <g transform="rotate(45,%d,%d)"></g>
    # ******************************
    def svg(self, offset={'x': 0, 'y': 0}):
        """Output the svg code for the shape (opacity is a function of fact/intuition)."""
        if self.node.true_points() >= self.node.false_points():
            colour = 'black'
        else:
            colour = 'red'
        if self.node.is_verifiable():
            opacity = 1.0
        else:
            opacity = 0.5
        l = self.l
        x = self.x - l/2
        y = self.y - l/2
        svg = '<a target="_blank" xlink:href="%s" target="_blank">' % self.node.theory_node.url()
        svg += '<rect x="%d" y="%d" width="%d" height="%d" fill="%s" fill-opacity="%0.2f" stroke-width="0">' % \
            (offset['x'] + x, offset['y'] + y, l, l, colour, opacity)
        svg += '<title>%s</title>' % str(self.node)
        svg += '</rect></a>'
        return svg


# ************************************************************
#
# ************************************************************
class SubtheoryShape(SpringShape):
    """A sub-class of spring shape for circle objects (sub-theories)."""

    # ******************************
    #
    # ******************************
    def __init__(self, node, x, y, area, colour='black', opacity=1.0):
        """Setup the repel radius for avoiding overlap."""
        self.node = node
        r = math.sqrt(area/PI)
        super().__init__(x, y, r, colour, opacity)

    # ******************************
    #
    # ******************************
    def svg_hidden(self, offset={'x': 0, 'y': 0}):
        """Output the svg code for the hidden-highlight shape."""
        r = self.r + 7.5
        svg = """<circle id="%s" visibility="hidden" cx="%d" cy="%d" r="%d" fill="none" stroke="lime" stroke-width="10"/>
              """ % (
            self.node.tag_id(),
            offset['x'] + self.x,
            offset['y'] + self.y,
            r,
        )
        return svg

    # ******************************
    #
    # ******************************
    def svg(self, offset={'x': 0, 'y': 0}):
        """Output the svg code for the shape (opacity is a function of fact/intuition)."""
        if self.node.true_points() >= self.node.false_points():
            colour = 'black'
        else:
            colour = 'red'
        svg = '<a target="_blank" xlink:href="%s" target="_blank">' % self.node.theory_node.url()
        svg += '<circle cx="%d" cy="%d" r="%d" fill="%s" stroke-width="0">' % \
            (offset['x'] + self.x, offset['y'] + self.y, self.r, colour)
        svg += '<title>%s</title>' % str(self.node)
        svg += '</circle></a>'
        return svg


# ************************************************************
# Class constants:
  # B: boundary or length of spring
  # K: spring force constant (see parent class for more details).
# ************************************************************
class Ring(SpringShape):
    """A sub-class of spring shape for ring objects (the true and false sets)."""

    # defines
    B = 5.0     # length of spring
    k = 1.0     # spring force constant

    # ******************************
    #
    # ******************************
    def __init__(self, x, y, r, colour='none', stroke_colour='black', opacity=0.25):
        """Setup the repel radius for avoiding overlap."""
        super().__init__(x, y, r, colour=colour, stroke_colour=stroke_colour, opacity=opacity)
        self.x_max = None
        self.x_min = None

    # ******************************
    #
    # ******************************
    def svg(self, offset={'x': 0, 'y': 0}):
        """Output the svg code for the shape."""
        svg = """<circle cx="%d" cy="%d" r="%d" fill="%s" stroke="%s" fill-opacity="%0.2f" stroke-width="4"/>
              """ % (offset['x'] + self.x, offset['y'] + self.y, self.r, self.colour, self.stroke_colour, self.opacity)
        return svg

    # ******************************
    #
    # ******************************
    def spring_force(self, object02, direction='in'):
        """Rings can only move horizontally, thus this method nullifies any vertical forces."""
        fx, fy = super().spring_force(object02, direction)
        return fx, 0

    # ******************************
    #
    # ******************************
    def propigate(self, dx, dy):
        """Rings cannot move outside of a boundary."""
        self.x += dx
        if self.x_max is not None:
            self.x = min(self.x, self.x_max)
        if self.x_min is not None:
            self.x = max(self.x, self.x_min)


# ************************************************************
#
# ************************************************************
class Wall(SpringShape):
    """A sub-class of spring shape for boundaries (no svg display)."""

    # ******************************
    #
    # ******************************
    def __init__(self, x, y):
        """Setup the repel boundary for avoiding shapes leave frame of view."""
        self.x = x
        self.y = y
        self.k = self.K
        assert x == None or y == None

    # ******************************
    #
    # ******************************
    def in_dist(self, object02):
        """Calculate distance to boundary."""
        if self.x is not None:
            dx = object02.x + object02.r - self.x
            dy = 0
        elif self.y is not None:
            dx = 0
            dy = object02.y - self.y
            if self.y <= 0:
                dy -= object02.r
                ud = dy
            else:
                dy += object02.r
                ud = -dy
        else:
            assert False

        d = abs(dx) + abs(dy)
        ux = 1.0*dx/d
        uy = 1.0*dy/d
        return ux, uy, ud

    # ******************************
    #
    # ******************************
    def svg(self):
        """This shape has nothing to display."""
        assert False

    # ******************************
    #
    # ******************************
    def out_dist(self, object02):
        """This shape only has an in force."""
        assert False


# *******************************************************************************
# Drawing classes
#
#
#
#
#
#
# *******************************************************************************


# ************************************************************
#
# ************************************************************
class Text():
    """A class for drawing text."""

    # ******************************
    #
    # ******************************
    def __init__(self, text, x, y, size=30, align='middle', bold=False, colour=None):
        """Create text."""
        self.text = text
        self.x = x
        self.y = y
        self.size = size
        self.bold = bold
        self.align = align
        self.colour = colour

    # ******************************
    #
    # ******************************
    def svg(self, offset={'x': 0, 'y': 0}):
        """Output the svg code for text."""
        svg = """<text text-anchor="%s" x="%d" y="%d" font-size="%d" """ % \
            (self.align, offset['x'] + self.x, offset['y'] + self.y, self.size)
        svg += """font-family="FreeSerif" """
        if self.bold:
            svg += """font-weight="bold" """
        if self.colour is not None:
            svg += """fill="%s" """ % self.colour
        svg = svg.strip() + ">%s</text>" % self.text
        return svg


# ************************************************************
#
# ************************************************************
class Circle():
    """A class for drawing circles."""

    # ******************************
    #
    # ******************************
    def __init__(self, x, y, r, colour='black', opacity=1.0):
        """Create a circle."""
        self.x = x
        self.y = y
        self.r = r
        self.colour = colour
        self.opacity = opacity

    # ******************************
    #
    # ******************************
    def svg(self, offset={'x': 0, 'y': 0}):
        """Output the svg code for shape."""
        svg = '<circle cx="%d" cy="%d" r="%d" fill="%s" fill-opacity="%0.2f" stroke="black" stroke-width="2.0"/>' % \
            (offset['x'] + self.x, offset['y'] +
             self.y, self.r, self.colour, self.opacity)
        return svg


# ************************************************************
#
# ************************************************************
class Rectangle():
    """A class for drawing rectangles."""

    # ******************************
    #
    # ******************************
    def __init__(self, x01, y01, x02, y02, colour='none', stroke_colour='black', stroke_width=2.0, opacity=1.0, hatch=False):
        """Create a rectangle."""
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
        self.colour = colour
        self.opacity = opacity
        self.hatch = hatch
        self.stroke_width = stroke_width
        self.stroke_colour = stroke_colour

    # ******************************
    # <g transform="rotate(0,%d,%d)"></g>
    # ******************************
    def svg(self, offset={'x': 0, 'y': 0}):
        """Output the svg code for shape."""
        svg = '<rect x="%d" y="%d" width="%d" height="%d"' % (
            self.x01, self.y01, self.x02-self.x01, self.y02-self.y01)
        if self.hatch:
            svg += ' style="fill: url(#hatch)"'
        else:
            svg += ' fill="%s"' % self.colour
        svg += ' stroke="%s" fill-opacity="%0.2f" stroke-width="%0.2f"/>' % (
            self.stroke_colour, self.opacity, self.stroke_width)
        return svg


# ************************************************************
#
# ************************************************************
class Wedge():
    """A class for drawing wedges (used for the pie-charts)."""

    # ******************************
    # Input arguments:
    # theta (deg):  theta01 < theta02 (arc of the wedge)
    # c_offset:     offset wedge point from center
    # explode:      offset entire wedge from center
    # ******************************
    def __init__(self, x, y, theta01, theta02, radius=100, c_offset=0.0, explode=0.0, colour='black', opacity=1.0):
        """Create a wedge."""
        self.x = x
        self.y = y
        self.theta01 = theta01
        self.theta02 = theta02
        self.radius = radius
        self.c_offset = c_offset
        self.explode = explode
        self.colour = colour
        self.opacity = opacity

    # ******************************
    # https://bocoup.com/blog/using-svg-patterns-as-fills
    # https://hackernoon.com/a-simple-pie-chart-in-svg-dbdd653b6936
    #  if self.hatch:
    #      fill = 'style="fill: url(#%sHatch)"' % self.colour
    #  else:
    #      fill = 'fill="%s"' % self.colour
    # ******************************
    def svg(self, offset={'x': 0, 'y': 0}):
        """Output the svg code for shape."""
        r = self.radius
        theta01 = math.radians(self.theta01)
        theta02 = math.radians(self.theta02)
        LARGE_ARC = int(self.theta02-self.theta01 > 180)

        dx00 = self.x + offset['x']
        dy00 = self.y + offset['y']

        x01 = 1.0 * r * math.cos(theta01)
        y01 = 1.0 * r * math.sin(theta01)
        x02 = 1.0 * r * math.cos(theta02)
        y02 = 1.0 * r * math.sin(theta02)

        dt = (theta02 + theta01)/2
        dr01 = self.explode
        dx01 = 1.0 * dr01 * math.cos(dt) + offset['x']
        dy01 = 1.0 * dr01 * math.sin(dt) + offset['y']

        dr02 = self.c_offset
        dx02 = 1.0 * dr02 * math.cos(dt) + offset['x']
        dy02 = 1.0 * dr02 * math.sin(dt) + offset['y']

        svg = """<path
                    fill="%s" fill-opacity="%0.2f" stroke="black" stroke-width="2.0"
                    d="M %0.2f,%0.2f L %0.2f,%0.2f A %0.2f,%0.2f 0 %d 1 %0.2f,%0.2f L %0.2f,%0.2f Z"
               />""" % (
            self.colour,
            self.opacity,
            dx00+dx01+dx02, dy00+dy01+dy02,
            x01+dx00+dx01, y01+dy00+dy01,
            r, r, LARGE_ARC,
            x02+dx00+dx01, y02+dy00+dy01,
            dx00+dx01+dx02, dy00+dy01+dy02
        )
        return svg


# ************************************************************
#
# ************************************************************
class Polygon():
    """A class for drawing polygons."""

    # ******************************
    # theta is in degrees
    # ******************************
    def __init__(self, path, colour='black', opacity=1.0):
        """Create a polygon with the given path."""
        self.path = path
        self.colour = colour
        self.opacity = opacity

    # ******************************
    # https://bocoup.com/blog/using-svg-patterns-as-fills
    # https://hackernoon.com/a-simple-pie-chart-in-svg-dbdd653b6936
    #  if self.hatch:
    #      svg += ' style="fill: url(#%sHatch)"' % self.colour
    #  else:
    #      svg += ' fill="%s"' % self.colour
    # ******************************
    def svg(self, offset={'x': 0, 'y': 0}):
        """Output the svg code for shape."""
        svg = '<path fill="%s" fill-opacity="%0.2f" stroke="black" stroke-width="1.0"' % (
            self.colour, self.opacity)
        svg += ' d="'
        for i, (x, y) in enumerate(self.path):
            if i == 0:
                svg += 'M '
            else:
                svg += ' L '
            svg += '%0.2f,%0.2f' % (x, y)
        svg += ' Z"/>'
        return svg


# ************************************************************
#
# ************************************************************
class Arrow():
    """A class for drawing arrows (currently only horizontal)."""

    # ******************************
    #
    # ******************************
    def __init__(self, x01, y01, x02, y02, width=2.5, colour='black'):
        """Create arrow with <x01,y01> as the start."""
        self.x01 = x01
        self.x02 = x02
        self.y01 = y01
        self.y02 = y02
        self.width = width
        self.colour = colour

    # ******************************
    # ToDo: this only works for horizontal arrows
    # ******************************
    def svg(self, offset={'x': 0, 'y': 0}):
        """Output the svg code for shape."""
        x01 = self.x01
        x02 = self.x02
        y01 = self.y01
        y02 = self.y02
        h = self.width*3

        svg = '<path fill="none" stroke="%s" stroke-width="%0.2f"' % (
            self.colour, self.width)
        svg += ' d="'
        svg += ' M %0.2f,%0.2f' % (x01, y01)
        svg += ' L %0.2f,%0.2f' % (x01, y01)
        if x02 > x01:
            svg += ' L %0.2f,%0.2f' % (x02-h, y02)
            svg += ' Z"/>'
            svg += '<path fill="%s" stroke="none"' % (self.colour)
            svg += ' d="'
            svg += ' M %0.2f,%0.2f' % (x02-2*h, y02-h)
            svg += ' Q %0.2f,%0.2f,%0.2f,%02.f' % (x02-h, y02, x02-2*h, y02+h)
            svg += ' L %0.2f,%0.2f' % (x02, y02)
        else:
            svg += ' L %0.2f,%0.2f' % (x02+h, y02)
            svg += ' Z"/>'
            svg += '<path fill="%s" stroke="none"' % (self.colour)
            svg += ' d="'
            svg += ' M %0.2f,%0.2f' % (x02+2*h, y02-h)
            svg += ' Q %0.2f,%0.2f,%0.2f,%02.f' % (x02+h, y02, x02+2*h, y02+h)
            svg += ' L %0.2f,%0.2f' % (x02, y02)
        svg += ' Z"/>'
        return svg


# ************************************************************
#
# ************************************************************
class Group():
    """A class for grouping svg objects."""

    # ******************************
    #
    # ******************************
    def __init__(self, tag_id='', hidden=False):
        """Create group with tag_id (optionally, hide group)."""
        self.tag_id = tag_id
        self.hidden = hidden
        self.shapes = []

    # ******************************
    #
    # ******************************
    def add(self, shape):
        """Add shape to group."""
        self.shapes.append(shape)

    # ******************************
    #
    # ******************************
    def svg(self, offset={'x': 0, 'y': 0, 'theta': 0.0}):
        """Output the svg code for the group."""
        if self.hidden:
            svg = '<g id="%s" visibility="hidden">' % self.tag_id
        else:
            svg = '<g id="%s">' % self.tag_id
        for shape in self.shapes:
            svg += shape.svg()
        svg += '</g>'
        return svg


# *******************************************************************************
# Diagrams
#
#
#
#
#
#
# *******************************************************************************


# ************************************************************
#
# ************************************************************
class PieChart():
    """A class for drawing pie-charts."""

    # defines
    RADIUS = 100
    GAP = 4
    C_OFFSET = 4
    OPACITY = 0.5
    BOARDER = {'top': 30, 'bottom': 30, 'left': 400, 'right': 400}

    # ******************************
    #
    # ******************************
    def __init__(self, data):
        """Create a pie-chart."""
        self.data = data
        self.shapes = []
        self.create_graph()

        R = self.RADIUS
        true_text = '%d' % int(
            round(100 * (self.data['true_facts'] + self.data['true_other'])))
        true_text += '% True Points'
        false_text = '%d' % int(
            round(100 * (self.data['false_facts'] + self.data['false_other'])))
        false_text += '% False Points'
        self.create_ledgend(-3*R, 0, true_text, 'black')
        self.create_ledgend(3*R, 0, false_text, 'red')

    # ******************************
    # ToDo: review GAP logic
    # ******************************
    def create_graph(self, data=None, offset={'x': 0, 'y': 0}):
        """Create the actual pie-chart using wedges."""

        # setup
        R = self.RADIUS
        GAP = self.GAP
        OPACITY = self.OPACITY
        C_OFFSET = self.C_OFFSET
        x = offset['x']
        y = offset['y']
        if data is None:
            data = self.data
        keys = ['true_other', 'true_facts', 'false_facts', 'false_other']

        # empty
        if sum(data.values()) == 0:
            c = Circle(x, y, R, colour='none')
            self.shapes.append(c)

        # count number of wedges to draw
        nWedges = 0
        for key in keys:
            if data[key] > 0.001:
                nWedges += 1
        nDegs = 360.0 - nWedges * GAP

        # true other
        if data['true_facts'] + data['true_other'] > 0:
            theta00 = 180.0 - 360.0 * \
                (data['true_facts'] + data['true_other'])/2 + GAP/2
        else:
            theta00 = 180.0 - GAP/2
        theta01 = theta00 + nDegs * data['true_other']
        if data['true_other'] > 0.001:
            if data['true_other'] > 0.999:
                c = Circle(x, y, R, colour='black', opacity=OPACITY)
                self.shapes.append(c)
            else:
                w = Wedge(x, y, theta00, theta01, R, c_offset=C_OFFSET,
                          colour='black', opacity=OPACITY)
                self.shapes.append(w)

        # true facts
        theta01 = theta01
        theta02 = theta01 + nDegs * data['true_facts']
        if data['true_facts'] > 0.001:
            theta01 += GAP
            theta02 += GAP
            if data['true_facts'] > 0.999:
                c = Circle(x, y, R, colour='black')
                self.shapes.append(c)
            else:
                w = Wedge(x, y, theta01, theta02, R,
                          c_offset=C_OFFSET, colour='black')
                self.shapes.append(w)

        # false facts
        theta01 = theta02
        theta02 = theta01 + nDegs * data['false_facts']
        if data['false_facts'] > 0.001:
            theta01 += GAP
            theta02 += GAP
            if data['false_facts'] > 0.999:
                c = Circle(x, y, R, colour='red')
                self.shapes.append(c)
            else:
                w = Wedge(x, y, theta01, theta02, R,
                          c_offset=C_OFFSET, colour='red')
                self.shapes.append(w)

        # false other
        theta01 = theta02
        theta02 = theta01 + nDegs * data['false_other']
        if data['false_other'] > 0.001:
            theta01 += GAP
            theta02 += GAP
            if data['false_other'] > 0.999:
                c = Circle(x, y, R, colour='red', opacity=OPACITY)
                self.shapes.append(c)
            else:
                w = Wedge(x, y, theta01, theta02, R,
                          c_offset=C_OFFSET, colour='red', opacity=OPACITY)
                self.shapes.append(w)
#        assert abs(theta02 - 360 - theta00) < 0.1

    # ******************************
    #
    # ******************************
    def create_ledgend(self, x=0, y=0, text=None, colour='black'):
        L = 20
        R = self.RADIUS
        OPACITY = self.OPACITY

        # facts
        x01 = x-60
        y01 = y
        self.shapes.append(
            Text('Facts', x=x01, y=y01-2*L, colour=colour, bold=True))
        self.shapes.append(Rectangle(x01-L, y01-L, x01+L,
                                     y01+L, colour=colour, opacity=1.0))

        # facts
        x01 = x+60
        y01 = y
        self.shapes.append(
            Text('Other', x=x01, y=y01-2*L, colour=colour, bold=True))
        self.shapes.append(Rectangle(x01-L, y01-L, x01+L,
                                     y01+L, colour=colour, opacity=OPACITY))

        # points
        if text is not None:
            self.shapes.append(
                Text(text, x=x, y=y+R, size=40, colour=colour, bold=True))

    # ******************************
    #
    # ******************************
    def output_svg(self):
        """Output the svg code for diagram."""
        R = self.RADIUS
        BOARDER = self.BOARDER
        offset = {'x': 0, 'y': 0}
        width = (2.0*R + BOARDER['left'] + BOARDER['right'])
        height = (2.0*R + BOARDER['top'] + BOARDER['bottom'])
        svg = """<center><svg baseProfile="full" version="1.1" viewBox="%d %d %d %d">
               """ % (-width/2 + offset['x'], -height/2 + offset['y'], width, height)

        for shape in self.shapes:
            svg += shape.svg()
        svg += """</svg></center>"""
        return svg

    # ******************************
    #
    # ******************************
    def output_text(self):
        """Output caption text for diagram."""
        return ''


# ************************************************************
#
# ************************************************************
class OpinionPieChart(PieChart):
    """A sub-class for opinion pie-charts."""

    # ******************************
    #
    # ******************************
    def __init__(self, opinion):
        """Create a pie chart visualizing the point distribution for the opinion."""
        self.opinion = opinion
        data = opinion.get_point_distribution()
        super().__init__(data)

    # ******************************
    #
    # ******************************
    def output_text(self):
        """Output caption text for diagram."""
        data = self.data
        text = """The above pie chart shows the point distribution of <b>%s's</b>
                   into true and false categories and facts and other (other is
                   anything other than facts). Below the breakdown is also shown
                   in the table below.
                """ % self.opinion.get_owner()
        text += '<br>'
        text += '<center>'
        text += '<div class="col-4">'
        text += '<table class="table-condensed table-borderless text-center" cellspacing="40">'
        text += '  <thead>'
        text += """  <tr>
                        <th style="width:10ex"/>
                        <th style="border-right:2px solid #000;"/>
                        <th style="width:10ex"> True </th>
                        <th style="width:10ex"> False </th>
                     </tr>"""
        text += """  <tr style="border-top:2px solid #000;">
                        <td/>
                        <th style="border-right:2px solid #000;"/>
                        <td/>
                        <td/>
                      </tr>"""
        text += '  </thead>'
        text += """<tr>
                      <th> Facts </th>
                      <th style="border-right:2px solid #000;"/>
                      <th> %d </th>
                      <th> %d </th>
                   </tr>""" % (
            round(100*data['true_facts']),
            round(100*data['false_facts']),
        )
        text += """<tr>
                      <th>Other</th>
                      <th style="border-right:2px solid #000;"/>
                      <th> %d </th>
                      <th> %d </th>
                   </tr>""" % (
            round(100*data['true_other']),
            round(100*data['false_other']),
        )
        text += '</table>'
        text += '</div>'
        text += '</center>'
        return text


# ************************************************************
#
# ************************************************************
class OpinionComparisionPieChart(OpinionPieChart):
    """A sub-class for side-by-side pie-charts (comparisons)."""

    # ******************************
    #
    # ******************************
    def __init__(self, opinion01, opinion02):
        """Create a side by side pie-chart for two opinions."""
        self.opinion01 = opinion01
        self.opinion02 = opinion02
        self.shapes = []

        data01 = opinion01.get_point_distribution()
        data02 = opinion02.get_point_distribution()
        self.create_graph(data01, offset={'x': -125, 'y': 0})
        self.create_graph(data02, offset={'x': 125, 'y': 0})

        R = self.RADIUS
        true_text = 'True Points'
        false_text = 'False Points'
        self.create_ledgend(-4*R, 0, true_text, 'black')
        self.create_ledgend(4*R, 0, false_text, 'red')

    # ******************************
    #
    # ******************************

    def output_text(self):
        """Output caption text for diagram."""
        data01 = self.opinion01.get_point_distribution()
        data02 = self.opinion02.get_point_distribution()
        text = """The above pie charts show the point distribution of <b>%s</b>
                   and <b>%s</b>. The points are broken down into true/false and
                   facts/other categories (other is non-factual evidence). Below
                   the breakdown is shown in tables.
                """ % (
            self.opinion01.get_owner(),
            self.opinion02.get_owner(),
        )
        text += '<br></br>'
        text += '<div class="row">'
        text += '<center>'
        text += '<div class="col-7">'
        text += '<table class="table-condensed table-borderless text-center" cellspacing="40">'
        text += '  <thead>'
#        text += """ <tr>
#                      <th/>
#                      <th/>
#                      <th style="width:60ex" colspan="2"> %s </th>
#                      <th/>
#                      <th style="width:60ex" colspan="2"> %s </th>
#                      <th/>
#                    </tr>""" % (
#                      self.opinion01.get_owner(),
#                      self.opinion02.get_owner(),
#                    )
        text += """ <tr>
                      <th style="width:20ex"/>
                      <th style="border-right:2px solid #000;"/>
                      <th style="width:15ex"> True </th>
                      <th style="width:15ex"> False </th>
                      <th style="border-right:2px solid #000;"/>
                      <th style="width:15ex"> True </th>
                      <th style="width:15ex"> False </th>
                      <th style="border-right:2px solid #000;"/>
                      <th style="width:10ex"/>
                      <th style="width:20ex"/>
                    </tr>"""
        text += """ <tr style="border-top:2px solid #000;">
                      <td/>
                      <th style="border-right:2px solid #000;"/>
                      <td/>
                      <td/>
                      <th style="border-right:2px solid #000;"/>
                      <td/>
                      <td/>
                      <th style="border-right:2px solid #000;"/>
                      <td/>
                    </tr>"""
        text += '  </thead>'
        text += """<tr>
                      <th>Facts</th>
                      <th style="border-right:2px solid #000;"/>
                      <th> %d&#37; </th>
                      <th> %d&#37; </th>
                      <th style="border-right:2px solid #000;"/>
                      <th> %d&#37; </th>
                      <th> %d&#37; </th>
                      <th style="border-right:2px solid #000;"/>
                   </tr>""" % (
            round(100*data01['true_facts']),
            round(100*data01['false_facts']),
            round(100*data02['true_facts']),
            round(100*data02['false_facts']),
        )
        text += """<tr>
                      <th>Other</th>
                      <th style="border-right:2px solid #000;"/>
                      <th> %d&#37; </th>
                      <th> %d&#37; </th>
                      <th style="border-right:2px solid #000;"/>
                      <th> %d&#37; </th>
                      <th> %d&#37; </th>
                      <th style="border-right:2px solid #000;"/>
                   </tr>""" % (
            round(100*data01['true_other']),
            round(100*data01['false_other']),
            round(100*data02['true_other']),
            round(100*data02['false_other']),
        )
        text += '</table>'
        text += '</div>'  # /col
        text += '</center>'
        text += '</div>'  # /row
        return text


# ************************************************************
#
# ************************************************************
class DemoPieChart(PieChart):
    """A sub-class for demo pie-charts (fake data)."""

    # ******************************
    #
    # ******************************
    def __init__(self):
        """Create a demo pie-chart with fake data."""
        R = [random.random() for i in range(4)]
        T = sum(R)
        R = [x/T for x in R]
        data = {
            'true_facts': R[0],
            'true_other': R[1],
            'false_facts': R[2],
            'false_other': R[3],
        }
        super().__init__(data)


# ************************************************************
#
# ************************************************************
class BarGraph():
    """A class for drawing bar graphs."""
    GAP = 2.0
    WIDTH = 600
    HEIGHT = 200
    BOARDER = {'top': 60, 'bottom': 75, 'left': 200, 'right': 200}
    OPACITY = 1.0

    # ******************************
    #
    # ******************************
    def __init__(self, data):
        """Create a bar graph."""
        self.data = data
        self.create_graph()
        self.create_ledgend()

    # ******************************
    #
    # ******************************
    def create_graph(self, data=None):
        """Create the actual bars for the graph."""
        W = self.WIDTH
        H = self.HEIGHT
        y00 = self.HEIGHT
        GAP = self.GAP
        max_h = max([x for x in self.data[0]])
        OPACITY = self.OPACITY
        self.shapes = []
        for i, h in enumerate(self.data[0]):
            if h > 0:
                x00 = self.data[1][i]
                x01 = self.data[1][i+1]
                if x01 <= 0:
                    colour = 'black'
                else:
                    colour = 'red'
                self.shapes.append(Rectangle(
                    x00*W+GAP, y00, x01*W-GAP, y00-h/max_h*H, colour=colour, stroke_colour='none'))

    # ******************************
    #
    # ******************************
    def create_ledgend(self):
        """Create the ledge for the graph."""

        # setup
        W = self.WIDTH
        H = self.HEIGHT
        GAP = self.GAP
        L = 20
        y00 = H

        # bottom boarder
        self.shapes.append(Rectangle(-W/2-20, y00, W/2+20,
                                     y00+3, opacity=1.0, colour='black'))
        # Tics
        x00 = -W/2
        y01 = y00+10
        dy = 30
        self.shapes.append(Rectangle(x00-GAP/4, y01, x00+GAP/4, y01+dy))
        x00 = -W/6
        self.shapes.append(Rectangle(x00-GAP/4, y01, x00+GAP/4, y01+dy))
        x00 = W/6
        self.shapes.append(Rectangle(x00-GAP/4, y01, x00+GAP/4, y01+dy))
        x00 = W/2
        self.shapes.append(Rectangle(x00-GAP/4, y01, x00+GAP/4, y01+dy))
        # Supporters - Moderates - Opposers
        x01 = -W/6-W/6
        y01 = y00+35
        self.shapes.append(
            Text('Supporters', x=x01, y=y01, size=30, bold=True))
        x01 = 0
        self.shapes.append(
            Text('Moderates', x=x01, y=y01, size=30, bold=True))
        x01 = W/6+W/6
        self.shapes.append(
            Text('Opposers', x=x01, y=y01, size=30, bold=True))

    # ******************************
    #
    # ******************************
    def create_ledgend02(self):
        """Create the ledge for the graph."""
        W = self.WIDTH
        H = self.HEIGHT
        GAP = self.GAP
        y00 = H

        # bottom boarder
        self.shapes.append(Rectangle(-W/2-40, y00, W/2+40,
                                     y00+3, opacity=1.0, colour='black'))
        # true tic
        x00 = -W/2
        self.shapes.append(
            Text('100', x=x00, y=y00+50, colour='black', bold=True))
        self.shapes.append(Text('%', x=x00+22, y=y00+50,
                                colour='black', bold=True, align='start'))
        self.shapes.append(Rectangle(x00-GAP/2, y00+7, x00 +
                                     GAP/2, y00+15, opacity=1.0, colour='black'))
        # mid tic
        x00 = 0
        self.shapes.append(Text('50', x=x00-10, y=y00+50,
                                colour='black', bold=True, align='end'))
        self.shapes.append(
            Text('/', x=x00, y=y00+50, colour='black', bold=True, align='middle'))
        self.shapes.append(Text('50', x=x00+10, y=y00+50,
                                colour='red', bold=True, align='start'))
        self.shapes.append(Text('%', x=x00+40, y=y00+50,
                                colour='red', bold=True, align='start'))
        self.shapes.append(Rectangle(x00-GAP/2, y00+7, x00 +
                                     GAP/2, y00+15, opacity=1.0, colour='black'))
        # false tic
        x00 = W/2
        self.shapes.append(
            Text('100', x=x00, y=y00+50, colour='red', bold=True))
        self.shapes.append(Text('%', x=x00+22, y=y00+50,
                                colour='red', bold=True, align='start'))
        self.shapes.append(Rectangle(x00-GAP/2, y00+7, x00 +
                                     GAP/2, y00+15, opacity=1.0, colour='black'))
        # True/False
        x01 = -W/2 - 100
        y01 = H
        self.shapes.append(
            Text('True', x=x01, y=y01, size=40, colour='black', bold=True))
        self.shapes.append(Text('False', x=-x01, y=y01,
                                size=40, colour='red', bold=True))
        # Supporters - Moderates - Opposers
        x01 = -W/6-W/6
        y01 = y00+90
        self.shapes.append(
            Text('Supporters', x=x01, y=y01, size=30, bold=True))
        x01 = 0
        self.shapes.append(
            Text('Moderates', x=x01, y=y01, size=30, bold=True))
        x01 = W/6+W/6
        self.shapes.append(
            Text('Opposers', x=x01, y=y01, size=30, bold=True))
        # Tics
        x01 = -W/2
        self.shapes.append(Rectangle(x01-GAP/4, y01-15, x01 +
                                     GAP/4, y01, opacity=1.0, colour='black'))
#        self.shapes.append(Arrow(x01+25, y01-7.5, x01+GAP, y01-7.5))
        x01 = -W/6
        self.shapes.append(Rectangle(x01-GAP/4, y01-15, x01 +
                                     GAP/4, y01, opacity=1.0, colour='black'))
#        self.shapes.append(Arrow(x01+25, y01-7.5, x01+GAP, y01-7.5))
#        self.shapes.append(Arrow(x01-25, y01-7.5, x01-GAP, y01-7.5))
        x01 = W/6
        self.shapes.append(Rectangle(x01-GAP/4, y01-15, x01 +
                                     GAP/4, y01, opacity=1.0, colour='black'))
#        self.shapes.append(Arrow(x01+25, y01-7.5, x01+GAP, y01-7.5))
#        self.shapes.append(Arrow(x01-25, y01-7.5, x01-GAP, y01-7.5))
        x01 = W/2
        self.shapes.append(Rectangle(x01-GAP/4, y01-15, x01 +
                                     GAP/4, y01, opacity=1.0, colour='black'))
#        self.shapes.append(Arrow(x01-25, y01-7.5, x01-GAP, y01-7.5))

        # True/False Users
#        x01 = -W/2-125; y01 = H-25
#        self.shapes.append(Text('True Users', x=x01, y=y01, size=30, colour='black', bold=True))
#        self.shapes.append(Text('False Users', x=-x01, y=y01, size=30, colour='red', bold=True))

        # facts
#        x01 = -W/2-125; y01 = 2/3*H
#        self.shapes.append(Text('True Users', x=x01, y=y01-2*L, colour="black", bold=True))
##        self.shapes.append(Rectangle(x01-L, y01-L, x01+L, y01+L, colour="black"))

#        # facts
#        x01 =  W/2+125; y01 = 2/3*H
#        self.shapes.append(Text('False Users', x=x01, y=y01-2*L, colour="red", bold=True))
##        self.shapes.append(Rectangle(x01-L, y01-L, x01+L, y01+L, colour="red"))

    # ******************************
    #
    # ******************************
    def output_svg(self):
        """Output the svg code for diagram."""
        W = self.WIDTH
        H = self.HEIGHT
        BOARDER = self.BOARDER
        offset = {'x': 0, 'y': -BOARDER['top']}
        width = W + BOARDER['left'] + BOARDER['right']
        height = H + BOARDER['top'] + BOARDER['bottom']
        svg = """<center><svg baseProfile="full" version="1.1" viewBox="%d %d %d %d">
               """ % (-width/2 + offset['x'], offset['y'], width, height)
        svg += """<defs>
                    <pattern id="hatch" patternUnits="userSpaceOnUse" patternTransform="rotate(45 0 0)" width="15" height="15">
                      <path d="M 0,0 L 15,0 M 0,0 L 0,15 Z" style="stroke:white; stroke-width:6.0" />
                    </pattern>
                  </defs>
               """
        for shape in self.shapes:
            svg += shape.svg()
        svg += """</svg></center>"""
        return svg

    # ******************************
    #
    # ******************************
    def output_text(self):
        """Output caption text for diagram."""
        return ''


# ************************************************************
#
# ************************************************************
class OpinionBarGraph(BarGraph):
    """A class for drawing opinion bar graphs."""

    # ******************************
    #
    # ******************************
    def __init__(self, opinion):
        """Create a bar graph for visualizing the point distribution awarded to a theory."""
        self.opinion = opinion
        self.theory = opinion.theory
        self.opinions = self.theory.get_opinions()

        bins = min(24, max(6, 6*(math.floor(self.opinions.count()/18) - 1)))
        data00 = [0.5 - x.true_points() for x in self.opinions]
        self.data = numpy.histogram(data00, bins=bins, range=(-0.5, 0.5))

        self.create_graph()
        self.create_hidden()
        self.create_ledgend()

    # ******************************
    #
    # ******************************
    def create_hidden(self, opinion=None, tag_id='user01'):
        """Create the hidden shapes that highlight opinion."""
        W = self.WIDTH
        H = self.HEIGHT
        y00 = self.HEIGHT
        GAP = self.GAP
        max_h = max([x for x in self.data[0]])

        if opinion is None:
            opinion = self.opinion

        true00, true01 = opinion.get_point_range()
        x00_true = -true00 + 0.5
        x01_true = -true01 + 0.5

        hidden_group01 = Group(tag_id=tag_id, hidden=True)
        for i, h in enumerate(self.data[0]):
            if h > 0:
                x00 = self.data[1][i]
                x01 = self.data[1][i+1]
                if (x00 <= x00_true and x01_true <= x01) or (x00_true <= x00 and x01 <= x01_true):
                    hidden_group01.add(
                        Rectangle(
                            x00*W+GAP,
                            y00,
                            x01*W-GAP,
                            y00-h/max_h*H,
                            hatch=True,
                            stroke_width=2.0,
                            stroke_colour='none',
                        )
                    )
        self.shapes.append(hidden_group01)

    # ******************************
    #
    # ******************************
    def output_text(self):
        """Output caption text for diagram."""
        stats = self.theory.get_stats(stats_type=models.Stats.TYPE.ALL)
        opinions = self.opinions

        text = """The above histogram shows the true/false belief distribution
                   of the <b>%d</b> %s (the most left column captures the
                   opinions that allocated 100&#37; of their points to the truth
                   of the theory). Hover the mouse below to highlight the bin
                   that the opinion falls into.
                """ % (
            opinions.count(),
            'opinion' if opinions.count() <= 1 else 'different opinions',
        )
        text += '<br></br>'
        text += '<center>'
        text += '  <a tag_id="user01" href="#"> Highlight %s </a>' % self.opinion.get_owner()
        text += '</center>'
        return text


# ************************************************************
#
# ************************************************************
class OpinionNodeBarGraph(BarGraph):
    """A class for drawing opinion-node bar graphs."""

    # ******************************
    #
    # ******************************
    def __init__(self, opinion_node):
        """Create a bar graph for visualizing the point distribution awarded to an opinion_node."""
        self.opinion_node = opinion_node
        self.theory_node = opinion_node.theory_node
        self.opinion_nodes = self.theory_node.opinion_nodes.all()

        bins = min(24, max(6, 6*(math.floor(self.opinion_nodes.count()/18) - 1)))
        data00 = [0.5 - x['true_points']
                  for x in self.opinion_nodes.values('true_points')]
        self.data = numpy.histogram(data00, bins=bins, range=(-0.5, 0.5))

        self.create_graph()
#        self.create_hidden()
        self.create_ledgend()


# ************************************************************
#
# ************************************************************
class OpinionComparisionBarGraph(OpinionBarGraph):
    """A class for drawing comparison bar graphs (two highlight opinions)."""

    # ******************************
    #
    # ******************************
    def __init__(self, opinion01, opinion02):
        """Create a bar graph for comparing two opinions."""
        self.theory = opinion01.theory
        self.opinion01 = opinion01
        self.opinion02 = opinion02
        self.opinions = self.theory.get_opinions()

        bins = min(24, max(6, 6*(math.floor(self.opinions.count()/18) - 1)))
        data00 = [0.5 - x.true_points() for x in self.opinions]
        self.data = numpy.histogram(data00, bins=bins, range=(-0.5, 0.5))
        self.create_graph()

        self.create_hidden(opinion01, tag_id='user01')
        self.create_hidden(opinion02, tag_id='user02')
        self.create_ledgend()

    # ******************************
    #
    # ******************************
    def output_text(self):
        """Output caption text for diagram."""
        stats = self.theory.get_stats(stats_type=models.Stats.TYPE.ALL)
        opinions = self.opinions

        text = """The above histogram shows the true/false belief distribution
                   of the <b>%d</b> %s (the most left column captures the
                   opinions that allocated 100&#37; of their points to the truth
                   of the theory). Hover the mouse below to highlight the bin
                   that the opinions falls into.
                """ % (
            opinions.count(),
            'opinion' if opinions.count() <= 1 else 'different opinions',
        )
        text += '<br></br>'
        text += '<div class="row">'
        text += '<div class="col-6 text-center">'
        text += ' <a tag_id="user01" href="#"> Highlight %s </a>' % self.opinion01.get_owner()
        text += '</div>'
        text += '<div class="col-6 text-center">'
        text += ' <a tag_id="user02" href="#"> Highlight %s </a>' % self.opinion02.get_owner()
        text += '</div>'
        text += '</div>'  # /row
        return text


# ************************************************************
#
# ************************************************************
class DemoBarGraph(BarGraph):
    """A class for drawing demo bar graphs (fake data)."""

    # ******************************
    #
    # ******************************
    def __init__(self):
        """Create a demo bar graph with fake data."""
        T = 0.0
        data = [[], [-0.5]]
        RES = 18
        for i in range(RES):
            x01 = -0.5 + 1.0*(i+1)/RES
            y00 = random.random()
            data[0].append(y00)
            data[1].append(x01)
            T += y00
        for i in range(RES):
            data[0][i] = data[0][i] / T
        super().__init__(data)


# ************************************************************
# ToDo: add opacity for sub-theories
# ToDo: add height and width
# ************************************************************
class OpinionVennDiagram():
    """A class for drawing Venn-diagrams."""

    # defines
    RADIUS = 150
    SHAPE_AREA = 0.6 * RADIUS**2
    BOARDER = {'top': 60, 'bottom': 30, 'left': 100, 'right': 100}

    # ******************************
    #
    # ******************************
    def __init__(self, opinion, flat=False, bottom_text=None):
        """Create a Venn-diagram that visualizes the opinion's nodes."""
        self.opinion = opinion
        self.flat = flat
        self.bottom_text = bottom_text

        self.calc_membership()
        self.create_rings()
        self.create_shapes()
        self.fix_overlap01()

        self.create_out_shapes()
        self.create_ledgend()
        self.create_boundary_shapes()
        self.fix_overlap02()

    # ******************************
    #
    # ******************************
    def __str__(self):
        """Output debug text for diagram (not yet implemented)."""
        return ''

    # ******************************
    #
    # ******************************
    def output_text(self):
        """Output caption text for diagram."""
        TRUE = self.opinion.is_true()
        text = """The above Venn-Diagram captures the evidence/sub-theories
                   that <b>%s</b> used as shapes. Squares represent evidence and
                   circles represent sub-theories, the size reflects the number
                   of points awarded, and the opacity reflects how factual the
                   evidence/sub-theory is.
                """ % (
            self.opinion.get_owner(),
        )
        return text

    # ******************************
    #
    # ******************************
    def output_svg(self):
        """Output the svg code for diagram."""
        R = self.RADIUS
        BOARDER = self.BOARDER
        height = (2.0*R + BOARDER['top'] + BOARDER['bottom'])
        width = 1200
        offset = {'x': width/2 - (self.true_ring.x + self.false_ring.x)/2,
                  'y': BOARDER['top'] + R - self.true_ring.y}
        svg = """<center><svg baseProfile="full" version="1.1" viewBox="0 0 %d %d">
                  <defs><style type="text/css"><![CDATA[.text { font-family: serif; fill: black; }]]></style></defs>
               """ % (width, height)
        # draw hidden elements first to appear below the rest
        for shape in self.true_shapes + self.int_shapes + self.false_shapes + self.out_shapes:
            svg += shape.svg_hidden(offset=offset)
        # draw the rest
        for shape in [self.true_ring, self.false_ring] + self.true_shapes + self.int_shapes + self.false_shapes + self.out_shapes:
            svg += shape.svg(offset=offset)
        for text in self.text:
            svg += text.svg(offset=offset)
        svg += """</svg></center>"""
        return svg

    # ******************************
    #
    # ******************************
    def calc_membership(self):
        """Group opinion nodes into the following sets: true, false, true &
           false, neither."""

        # setup
        self.true_set = []
        self.int_set = []
        self.false_set = []
        self.out_set = []
        if self.flat:
            nodes = self.opinion.get_flat_nodes()
        else:
            nodes = self.opinion.get_nodes()

        # blah
        for node in nodes:
            if node.total_points() < 0.01:
                if node.total_points() > 0:
                    self.out_set.append(node)
            elif node.true_ratio() >= 0.66:
                self.true_set.append(node)
            elif node.false_ratio() >= 0.66:
                self.false_set.append(node)
            else:
                self.int_set.append(node)

    # ******************************
    #
    # ******************************
    def create_rings(self):
        """Create true and false rings."""
        R = self.RADIUS
        # fix rings
        if len(self.int_set) == 0:
            self.true_ring = Ring(-0.85*R, 0.0, R)
            self.false_ring = Ring(0.85*R, 0.0, R)
        # overlap rings
        else:
            self.true_ring = Ring(-0.75*R, 0.0, R)
            self.false_ring = Ring(0.75*R, 0.0, R)
        self.true_ring.x_max = -0.35*R
        self.false_ring.x_min = 0.35*R

    # ******************************
    #
    # ******************************
    def create_shapes(self):
        """Create evidence and sub-theory shapes (within the true and false sets)."""
        R = self.RADIUS
        random.seed(0)

        self.true_shapes = []
        for node in self.true_set:
            # randomly place the shape inside the positive ring
            r = math.sqrt(random.random()) * R
            theta = math.radians(random.randint(0, 360))
            x = self.true_ring.x + r * math.cos(theta)
            y = self.true_ring.y + r * math.sin(theta)
            # create shapes
            area = self.SHAPE_AREA * node.total_points()
            if node.is_theory():
                self.true_shapes.append(SubtheoryShape(node, x, y, area))
            elif node.is_evidence():
                self.true_shapes.append(EvidenceShape(node, x, y, area))

        self.int_shapes = []
        for node in self.int_set:
            # randomly place the shape inside the positive ring
            r = math.sqrt(random.random()) * R
            theta = math.radians(random.randint(0, 360))
            x = (self.true_ring.x + self.false_ring.x)/2 + r * math.cos(theta)
            y = (self.true_ring.y + self.false_ring.y)/2 + r * math.sin(theta)
            # create shapes
            area = self.SHAPE_AREA * node.total_points()
            if node.is_theory():
                self.int_shapes.append(SubtheoryShape(node, x, y, area))
            elif node.is_evidence():
                self.int_shapes.append(EvidenceShape(node, x, y, area))

        self.false_shapes = []
        for node in self.false_set:
            # randomly place the shape inside the positive ring
            r = math.sqrt(random.random()) * R
            theta = math.radians(random.randint(0, 360))
            x = self.false_ring.x + r * math.cos(theta)
            y = self.false_ring.y + r * math.sin(theta)
            # create shapes
            area = self.SHAPE_AREA * node.total_points()
            if node.is_theory():
                self.false_shapes.append(SubtheoryShape(node, x, y, area))
            elif node.is_evidence():
                self.false_shapes.append(EvidenceShape(node, x, y, area))

    # ******************************
    #
    # ******************************
    def create_out_shapes(self):
        """Create evidence and sub-theory shapes that falls outside of the true and false sets."""
        R = self.RADIUS
        BOARDER = self.BOARDER
        X_NEG = self.true_ring.x - R - BOARDER['left']
        X_POS = self.false_ring.x + R + BOARDER['right']
        X_WID = X_POS - X_NEG
        Y_NEG = self.true_ring.y + R + BOARDER['top']
        Y_POS = self.true_ring.y - R - BOARDER['bottom']
        Y_WID = Y_POS - Y_NEG

        random.seed(0)
        self.out_shapes = []
        for node in self.out_set:
            # randomly place shapes inside frame
            x = random.random() * X_WID + X_NEG
            y = random.random() * Y_WID + Y_NEG
            # create shapes
            area = self.SHAPE_AREA * node.total_points()
            if node.is_theory():
                self.out_shapes.append(SubtheoryShape(node, x, y, area))
            elif node.is_evidence():
                self.out_shapes.append(EvidenceShape(node, x, y, area))

    # ******************************
    #
    # ******************************
    def create_boundary_shapes(self):
        """Create boundary shapes to confine the shapes to the view port."""
        BOARDER = self.BOARDER
        R = self.RADIUS
        X_NEG = self.true_ring.x - R - BOARDER['left']
        X_POS = self.false_ring.x + R + BOARDER['right']
        X_WID = X_POS - X_NEG
        Y_POS = self.true_ring.y - R - BOARDER['top']
        Y_NEG = self.true_ring.y + R + BOARDER['bottom']
        Y_WID = Y_POS - Y_NEG

        # image frame
        self.in_boundry_shapes = []
        self.in_boundry_shapes.append(Wall(None, Y_POS))
        self.in_boundry_shapes.append(Wall(None, Y_NEG))
        self.in_boundry_shapes.append(
            Ring((X_NEG + X_POS)/2, self.true_ring.y, X_WID/2))

        # create a circle to avoid the text and middle of the figure
        x = (self.true_ring.x + self.false_ring.x)/2
        y = self.true_ring.y
        R = (self.false_ring.x - self.true_ring.x)/2 + 1*R
        self.out_boundry_shapes = [Ring(x, y, R)]

    # ******************************
    #
    # ******************************
    def fix_overlap01(self):
        """Move the inside shapes around to avoid overlap."""
        # setup
        shapes = []
        if len(self.int_shapes) > 0:
            shapes.append({'prop': self.true_shapes, 'in': [
                          self.true_ring], 'out': self.true_shapes+[self.false_ring]})
            shapes.append({'prop': self.false_shapes, 'in': [
                          self.false_ring], 'out': self.false_shapes+[self.true_ring]})
            shapes.append({'prop': self.int_shapes, 'in': [
                          self.true_ring, self.false_ring], 'out': self.int_shapes})
            shapes.append({'prop': [
                          self.true_ring], 'in': self.true_shapes + self.int_shapes, 'out': self.false_shapes})
            shapes.append({'prop': [
                          self.false_ring], 'in': self.false_shapes + self.int_shapes, 'out': self.true_shapes})
        else:
            shapes.append({'prop': self.true_shapes, 'in': [
                          self.true_ring], 'out': self.true_shapes+[self.false_ring]})
            shapes.append({'prop': self.false_shapes, 'in': [
                          self.false_ring], 'out': self.false_shapes+[self.true_ring]})
        # propagate
        self.propagate(shapes)

    # ******************************
    #
    # ******************************
    def fix_overlap02(self):
        """Move the outside shapes around to avoid overlap."""
        # setup
        shapes = [{'prop': self.out_shapes, 'in': self.in_boundry_shapes,
                   'out': self.out_boundry_shapes + self.out_shapes}]
        for shape in [self.true_ring, self.false_ring]:
            shape.reset_k()
        # propagate
        self.propagate(shapes)

    # ******************************
    #
    # ******************************
    def propagate(self, shapes):
        """Incrementally propagate the spring-class shapes to avoid overlap."""
        for step in range(100):
            max_step = 0.0
            for shape_set in shapes:
                for shape01 in shape_set['prop']:
                    total_x_force = 0.0
                    total_y_force = 0.0
                    for shape02 in shape_set['out']:
                        if shape02 != shape01:
                            fx, fy = shape01.get_force(
                                shape02, direction='out')
                            total_x_force += fx
                            total_y_force += fy
                    for shape02 in shape_set['in']:
                        fx, fy = shape01.get_force(shape02, direction='in')
                        total_x_force += fx
                        total_y_force += fy
                    max_step = max(
                        [max_step, abs(total_x_force), abs(total_y_force)])
                    shape01.propigate(total_x_force, total_y_force)
            if max_step < 0.01:
                break

    # ******************************
    #
    # ******************************
    def create_ledgend(self):
        """Create legend text."""
        self.text = []
        R = self.RADIUS
        BOARDER = self.BOARDER
        self.text.append(Text('True', x=self.true_ring.x, y=self.true_ring.y -
                              1.0*13/12*R, size=40, colour='black', bold=True))
        self.text.append(Text('False', x=self.false_ring.x,
                              y=self.true_ring.y - 1.0*13/12*R, size=40, colour='red', bold=True))
        if self.bottom_text is not None:
            self.text.append(Text(self.bottom_text, x=(
                self.true_ring.x + self.false_ring.x)/2, y=0.95*R + BOARDER['bottom']))

    # ******************************
    #
    # ******************************
    def get_collaborative_evidence(self, sort_list=False):
        """Return a list of evidence/sub-theories that support the opinion."""
        if self.opinion.is_true():
            evidence = self.true_set
        else:
            evidence = self.false_set
        if sort_list:
            output_set = sorted(
                evidence, key=lambda x: x.total_points(), reverse=True)
            while len(output_set) > 0 and output_set[-1].total_points() < 0.01:
                output_set.pop()
            return output_set
        else:
            return evidence

    # ******************************
    #
    # ******************************
    def get_contradicting_evidence(self, sort_list=False):
        """Return a list of evidence/sub-theories that contradicts the opinion."""
        if self.opinion.is_true():
            evidence = self.false_set
        else:
            evidence = self.true_set
        if sort_list:
            output_set = sorted(
                evidence, key=lambda x: x.total_points(), reverse=True)
            while len(output_set) > 0 and output_set[-1].total_points() < 0.01:
                output_set.pop()
            return output_set
        else:
            return evidence

    # ******************************
    #
    # ******************************
    def get_controversial_evidence(self, sort_list=False):
        """Return a list of evidence/sub-theories that is used to both support and contradict the opinion."""
        if sort_list:
            output_set = sorted(
                self.int_set, key=lambda x: x.total_points(), reverse=True)
            while len(output_set) > 0 and output_set[-1].total_points() < 0.01:
                output_set.pop()
            return output_set
        else:
            return self.int_set

    # ******************************
    #
    # ******************************
    def get_unaccounted_evidence(self, sort_list=False):
        """Return a list of evidence/sub-theories that is insignificant to the opinion."""
        if sort_list:
            output_set = sorted(
                self.out_set, key=lambda x: x.total_points(), reverse=True)
            while len(output_set) > 0 and output_set[-1].total_points() < 0.01:
                output_set.pop()
            return output_set
        else:
            return self.out_set


# ************************************************************
#
# ************************************************************
class OpinionComparisionVennDiagram(OpinionVennDiagram):
    """A class for drawing relative Venn-diagrams (used for comparisons)."""

    # ******************************
    #
    # ******************************
    def __init__(self, opinion01, opinion02, flat=False, bottom_text=None):
        """Create a Venn-diagram comparing the two opinions."""
        self.opinion01 = opinion01
        self.opinion02 = opinion02
        self.opinion = opinion01
        self.flat = flat
        self.bottom_text = bottom_text

        self.calc_membership()
        self.create_rings()
        self.create_shapes()
        self.fix_overlap01()

        self.create_out_shapes()
        self.create_ledgend()
        self.create_boundary_shapes()
        self.fix_overlap02()

    # ******************************
    #
    # ******************************
    def calc_membership(self):
        """Group opinion nodes into the following sets: true, false, true &
           false, neither. The size, colour, and opacity of the nodes is
           determined by opinion02."""

        # setup sets
        self.true_set = []
        self.int_set = []
        self.false_set = []
        self.out_set = []

        # setup nodes
        theory = self.opinion01.theory
        if self.flat:
            nodes = theory.get_flat_nodes()
            get_node01 = self.opinion01.get_flat_node
            get_node02 = self.opinion02.get_flat_node
        else:
            nodes = theory.get_nodes()
            get_node01 = self.opinion01.get_node
            get_node02 = self.opinion02.get_node

        # blah
        for theory_node in nodes:

            # get or create node01
            points_node01 = get_node01(theory_node=theory_node)
            if points_node01 is None:
                points_node01 = NodePointerBase.create(
                    parent=self.opinion01,
                    theory_node=theory_node,
                    true_points=0.0,
                    false_points=0.0,
                )
            # get or create node02
            points_node02 = get_node02(theory_node=theory_node)
            if points_node02 is None:
                points_node02 = NodePointerBase.create(
                    parent=self.opinion02,
                    theory_node=theory_node,
                    true_points=0.0,
                    false_points=0.0,
                )

            # assign nodes to sets
            if points_node01.total_points() < 0.01:
                if points_node02.total_points() > 0:
                    self.out_set.append(points_node02)
            elif points_node01.true_ratio() >= 0.66:
                if points_node02.total_points() > 0:
                    self.true_set.append(points_node02)
            elif points_node01.false_ratio() >= 0.66:
                if points_node02.total_points() > 0:
                    self.false_set.append(points_node02)
            else:
                if points_node02.total_points() > 0:
                    self.int_set.append(points_node02)

    # ******************************
    #
    # ******************************
    def output_text(self):
        """Output caption text for diagram."""
        TRUE = self.opinion01.true_points() >= self.opinion01.false_points()
        text = """The above Venn-Diagram captures the evidence/sub-theories
                   that <b>%s</b> used to construct their opinion. The size,
                   colour, and opacity reflect the belief of <b>%s's</b> opinion.
                """ % (
            self.opinion01.get_owner(),
            self.opinion02.get_owner(),
        )
        return text


# *******************************************************************************
#
# *******************************************************************************
class DemoVennDiagram(OpinionVennDiagram):
    """A class for drawing demo Venn-diagrams (fake data)."""

    # ******************************
    # Remove normalization?
    # ******************************
    def __init__(self, true_set_size=10, int_set_size=10, false_set_size=10, out_set_size=10):
        """Create a demo Venn-diagram with fake data."""
        random.seed()
        seed = random.randint(0, 100)
#        seed = 72
        random.seed(seed)

        opinion = models.Opinion.get_demo()
        theory = opinion.theory
        theory_nodes = list(theory.nodes.all())

        opinion.saved_true_points = opinion.true_points()
        opinion.saved_false_points = opinion.false_points()

        total_true_points = 0
        total_false_points = 0
        opinion.saved_nodes = []

        for i in range(random.randint(1, true_set_size)):
            new_node = NodePointerBase.create(
                parent=opinion,
                theory_node=random.choice(theory_nodes),
                true_points=random.randint(1, 100),
                false_points=random.randint(1, 10),
            )
            opinion.saved_nodes.append(new_node)
            total_true_points += new_node.true_points()
            total_false_points += new_node.false_points()

        for i in range(random.randint(1, int_set_size)):
            new_node = NodePointerBase.create(
                parent=opinion,
                theory_node=random.choice(theory_nodes),
                true_points=random.randint(1, 10),
                false_points=random.randint(1, 10),
            )
            opinion.saved_nodes.append(new_node)
            total_true_points += new_node.true_points()
            total_false_points += new_node.false_points()

        for i in range(random.randint(1, false_set_size)):
            new_node = NodePointerBase.create(
                parent=opinion,
                theory_node=random.choice(theory_nodes),
                true_points=random.randint(1, 10),
                false_points=random.randint(1, 100),
            )
            opinion.saved_nodes.append(new_node)
            total_true_points += new_node.true_points()
            total_false_points += new_node.false_points()

        for i in range(random.randint(1, out_set_size)):
            new_node = NodePointerBase.create(
                parent=opinion,
                theory_node=random.choice(theory_nodes),
                true_points=random.randint(1, 5),
                false_points=random.randint(1, 5),
            )
            opinion.saved_nodes.append(new_node)
            total_true_points += new_node.true_points()
            total_false_points += new_node.false_points()

        # normalize points to create the weights
        for node in opinion.saved_nodes:
            if total_true_points > 0:
                node.saved_true_points = (
                    node.true_points() / total_true_points) * opinion.true_points()
            else:
                node.saved_true_points = 0.0
            if total_false_points > 0:
                node.saved_false_points = (
                    node.false_points() / total_false_points) * opinion.false_points()
            else:
                node.saved_false_points = 0.0

        super().__init__(opinion, bottom_text=str(seed))

    # ******************************
    #
    # ******************************
    def output_text(self):
        """Output caption text for diagram."""
        return ''


# *******************************************************************************
#
# *******************************************************************************
if __name__ == "__main__":
    c = VennDiagram(10, 0, 10)
    print(c.output())
