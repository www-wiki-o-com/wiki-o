"""  __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

A web service for sharing opinions and avoiding arguments

@file       theories/graph_lib/pie_charts.py
@brief      A collection of classes for creating, viewing, and manipulating pie charts
@copyright  GNU Public License, 2018
@authors    Frank Imeson
"""


# *******************************************************************************
# imports
# *******************************************************************************
import random

from theories.graph_lib.shapes import offset_xy
from theories.graph_lib.shapes import Colour, Circle, Wedge, Text, Rectangle


# *******************************************************************************
# Diagrams
#
#
#
#
#
#
# *******************************************************************************


class PieChart():
    """A class for drawing pie-charts."""

    # Constants
    DEFAULT_CONFIG = {'radius':100, 'c_offset':4, 'gap':4}
    DEFAULT_BOARDER = {'top': 30, 'bottom': 30, 'left': 400, 'right': 400}

    def __init__(self, data, config=None, boarder=None):
        """Constructor for the PieChart class.

        Args:
            data (dict('true_facts':float, 'true_other':float, 'false_facts':float,
                'false_other':float)): The set of data to be used for the pie chart.
            config (dict('radius':float, 'c_offset':float, 'gap':float), optional):
                The configuration. Defaults to None.
            boarder (dict('top':float, 'bottom':float, 'left':float', 'right':float), optional):
                The bounding box used to size the diagram. Defaults to None.
        """
        self.data = data
        self.shapes = []
        if config is None:
            self.config = self.DEFAULT_CONFIG
        else:
            self.config = config
        if boarder is None:
            self.boarder = self.DEFAULT_BOARDER
        else:
            self.boarder = boarder
        self.construct()

    def construct(self):
        """Construct the diagram."""
        # Setup
        r = self.config['radius']
        true_points = int(round(100 * (self.data['true_facts'] + self.data['true_other'])))
        false_points = int(round(100 * (self.data['false_facts'] + self.data['false_other'])))
        true_text = '{}% True Points'.format(true_points)
        false_text = '{}% False Points'.format(false_points)

        # Construct
        self.create_graph()
        self.create_ledgend(-3*r, 0, true_text, Colour.BLACK)
        self.create_ledgend(3*r, 0, false_text, Colour.RED)

    def create_graph(self, data=None, offset=None):
        """Create the actual pie-chart using wedges.

        The individual wedges are created one by one by keeping track of the previous and
        next theta.

        Args:
            data (dict('true_facts':float, 'true_other':float, 'false_facts':float,
                'false_other':float)): The set of data to be used for the pie chart.
            offset (dict('x':float, 'y':float), optional): The x,y offset dict to be used.
                Defaults to None.
        """
        # Setup
        r = self.config['radius']
        gap = self.config['gap']
        c_offset = self.config['c_offset']
        x, y = offset_xy(0, 0, offset)
        if data is None:
            data = self.data
        keys = ['true_other', 'true_facts', 'false_facts', 'false_other']

        # Empty
        if sum(data.values()) == 0:
            empty_circle = Circle(x, y, r, colour=Colour.NONE)
            self.shapes.append(empty_circle)

        # Count number of wedges to draw
        num_wedges = 0
        for key in keys:
            if data[key] > 0.001:
                num_wedges += 1
        num_degs = 360.0 - num_wedges * gap

        # Find the initial theta00 for the first wedge (true_other). The pie chart is constructed
        # to have the true data at the left. To achieve this we take the average of the true points
        # as our offset (the midpoint of the true data will be the top). Additionally, we add a gap
        # in between the wedges for astetics.
        if data['true_facts'] + data['true_other'] > 0:
            theta00 = 180.0 - 360.0*(data['true_facts'] + data['true_other'])/2 + gap/2
        else:
            theta00 = 180.0 - gap/2

        # Construct the true_other wedge
        theta01 = theta00 + num_degs * data['true_other']
        if data['true_other'] > 0.001:
            if data['true_other'] > 0.999:
                full_circle = Circle(x, y, r, colour=Colour.BLACK)
                self.shapes.append(full_circle)
            else:
                wedge = Wedge(x, y, theta00, theta01, r, c_offset=c_offset, colour=Colour.GREY)
                self.shapes.append(wedge)

        # Construct the true_facts wedge
        theta02 = theta01 + num_degs * data['true_facts']
        if data['true_facts'] > 0.001:
            theta01 += gap
            theta02 += gap
            if data['true_facts'] > 0.999:
                full_circle = Circle(x, y, r, colour=Colour.BLACK)
                self.shapes.append(full_circle)
            else:
                wedge = Wedge(x, y, theta01, theta02, r, c_offset=c_offset, colour=Colour.BLACK)
                self.shapes.append(wedge)

        # Construct the false_facts wedge
        theta01 = theta02
        theta02 = theta01 + num_degs * data['false_facts']
        if data['false_facts'] > 0.001:
            theta01 += gap
            theta02 += gap
            if data['false_facts'] > 0.999:
                full_circle = Circle(x, y, r, colour=Colour.RED)
                self.shapes.append(full_circle)
            else:
                wedge = Wedge(x, y, theta01, theta02, r, c_offset=c_offset, colour=Colour.RED)
                self.shapes.append(wedge)

        # Construct the false_other wedge
        theta01 = theta02
        theta02 = theta01 + num_degs * data['false_other']
        if data['false_other'] > 0.001:
            theta01 += gap
            theta02 += gap
            if data['false_other'] > 0.999:
                full_circle = Circle(x, y, r, colour=Colour.PINK)
                self.shapes.append(full_circle)
            else:
                wedge = Wedge(x, y, theta01, theta02, r, c_offset=c_offset, colour=Colour.PINK)
                self.shapes.append(wedge)
        # assert (theta02 - theta00 + 360) % 360 < 0.1

    def create_ledgend(self, x=0, y=0, points_text=None, colour=Colour.BLACK):
        """Creates a True or False ledge for the pie chart.

        Args:
            x (float, optional): The x coordinate. Defaults to 0.
            y (float, optional): The y coordinate. Defaults to 0.
            points_text (str, optional): The points text. Defaults to None.
            colour (Colour, optional): The ledgend colour (RED or BLACK). Defaults to Colour.BLACK.
        """
        # Setup
        r = self.config['radius']
        length = 20

        # Construct the facts ledgend
        x01, y01 = (x - 60, y)
        self.shapes.append(Text('Facts', x=x01, y=y01-2*length, colour=colour, bold=True))
        self.shapes.append(Rectangle(x01-length, y01-length, x01+length, y01+length, colour=colour))

        # Construct the other ledgend
        x01, y01 = (x + 60, y)
        self.shapes.append(Text('Other', x=x01, y=y01-2*length, colour=colour, bold=True))
        self.shapes.append(Rectangle(x01-length, y01-length, x01+length, y01+length,
                                     colour=Colour.get_transparent_colour(Colour, colour)))

        # Add the points text
        if points_text is not None:
            self.shapes.append(Text(points_text, x=x, y=y+r, size=40, colour=colour, bold=True))

    def get_svg(self):
        """Output the svg code for the diagram.

        Returns:
            str: The svg code for displaying the diagram.
        """
        # Setup
        r = self.config['radius']
        boarder = self.boarder
        offset = {'x': 0, 'y': 0}
        width = (2.0*r + boarder['left'] + boarder['right'])
        height = (2.0*r + boarder['top'] + boarder['bottom'])

        # SVG
        svg = '<center><svg baseProfile="full" version="1.1"'
        svg += ' viewBox="%d %d' % (-width/2 + offset['x'], -height/2 + offset['y'])
        svg += ' %d %d">' % (width, height)
        for shape in self.shapes:
            svg += shape.get_svg()
        svg += """</svg></center>"""
        return svg

    def get_caption(self):
        """Dummy method, there is no caption text for this diagram.

        Returns:
            str: blank
        """
        return ''


class OpinionPieChart(PieChart):
    """A sub-class for opinion pie-charts."""

    def __init__(self, opinion=None):
        """Constructor for the OpinionPieChart class.

        Used to create a pie chart visualizing the point distribution for the opinion.

        Args:
            opinion (OpinionNode, optional): The opinion to visualize. Defaults to None.
        """
        self.opinion = opinion
        if opinion is None:
            data = None
        else:
            data = opinion.get_point_distribution()
        super().__init__(data)

    def get_caption(self):
        """Output caption text for diagram.

        Returns:
            str: The html text for the diagram's caption.
        """
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
                   </tr>""" % (round(100*data['true_facts']), round(100*data['false_facts']))
        text += """<tr>
                      <th>Other</th>
                      <th style="border-right:2px solid #000;"/>
                      <th> %d </th>
                      <th> %d </th>
                   </tr>""" % (round(100*data['true_other']), round(100*data['false_other']))
        text += '</table>'
        text += '</div>'
        text += '</center>'
        return text


class OpinionComparisionPieChart(OpinionPieChart):
    """A sub-class for side-by-side pie-charts (comparisons)."""

    def __init__(self, opinion01, opinion02):
        """Create a side by side pie-chart for two opinions.

        Args:
            opinion01 (OpinionNode): The left opinion for the comparision.
            opinion02 (OpinionNode): The right opinion for the comparision.
        """
        self.opinion01 = opinion01
        self.opinion02 = opinion02
        self.shapes = []
        super().__init__(None)

    def construct(self):
        """Construct the diagram."""
        # Setup
        r = self.config['radius']
        true_text = None
        false_text = None

        # Construct
        data01 = self.opinion01.get_point_distribution()
        data02 = self.opinion02.get_point_distribution()
        self.create_graph(data01, offset={'x': -125, 'y': 0})
        self.create_graph(data02, offset={'x': 125, 'y': 0})
        self.create_ledgend(-4*r, 0, true_text, Colour.BLACK)
        self.create_ledgend(4*r, 0, false_text, Colour.RED)

    def get_caption(self):
        """Output caption text for diagram.

        Returns:
            str: The html text for the diagram's caption.
        """
        text = """The above pie charts show the point distribution of <b>%s</b>
                   and <b>%s</b>. The points are broken down into true/false and
                   facts/other categories (other is non-factual evidence). Below
                   the breakdown is shown in tables.
                """ % (self.opinion01.get_owner(), self.opinion02.get_owner())
        return text


class DemoPieChart(PieChart):
    """A sub-class for demo pie-charts (fake data)."""

    def __init__(self):
        """Create a demo pie-chart with fake data."""
        points = [random.random() for i in range(4)]
        total_points = sum(points)
        points = [x/total_points for x in points]
        data = {
            'true_facts': points[0],
            'true_other': points[1],
            'false_facts': points[2],
            'false_other': points[3],
        }
        super().__init__(data)


# *******************************************************************************
# main (used for testing)
# *******************************************************************************
if __name__ == "__main__":
    pass
