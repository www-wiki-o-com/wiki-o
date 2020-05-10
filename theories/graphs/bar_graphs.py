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
import numpy

from theories.graphs.shapes import Colour, Text, Rectangle, Group

# *******************************************************************************
# Diagrams
#
#
#
#
#
#
# *******************************************************************************


class BarGraph():
    """A class for drawing bar graphs."""

    # Constants
    DEFAULT_CONFIG = {'gap': 2.0, 'width': 600, 'height': 200}
    DEFAULT_BOARDER = {'top': 60, 'bottom': 75, 'left': 200, 'right': 200}

    def __init__(self, data, config=None, boarder=None):
        """Create a bar graph.

        Args:
            data (list(float)): A list of bar heights.
            config (dict, optional): A diagram configurations. Defaults to None.
            boarder (dict, optional): The boarder configuration. Defaults to None.
        """
        if config is None:
            self.config = self.DEFAULT_CONFIG
        else:
            self.config = config
        if boarder is None:
            self.boarder = self.DEFAULT_BOARDER
        else:
            self.boarder = boarder
        self.data = data
        self.shapes = None
        self.construct()

    def construct(self):
        """Construct the diagram."""
        self.create_graph()
        self.create_ledgend()

    def create_graph(self):
        """Create the actual bars for the graph."""
        # Setup
        width = self.config['width']
        height = self.config['height']
        gap = self.config['gap']

        y00 = height
        max_h = max(self.data[0])

        self.shapes = []
        for i, h in enumerate(self.data[0]):
            if h > 0:
                x00 = self.data[1][i]
                x01 = self.data[1][i + 1]
                if x01 <= 0:
                    colour = Colour.BLACK
                else:
                    colour = Colour.RED
                self.shapes.append(
                    Rectangle(x00 * width + gap,
                              y00,
                              x01 * width - gap,
                              y00 - h / max_h * height,
                              colour=colour,
                              stroke_colour=Colour.NONE))

    def create_ledgend(self):
        """Create the ledge for the graph."""
        # Setup
        width = self.config['width']
        height = self.config['height']
        gap = self.config['gap']

        # Construct the bottom boarder.
        y00 = height
        self.shapes.append(
            Rectangle(-width / 2 - 20, y00, width / 2 + 20, y00 + 3, colour=Colour.BLACK))

        # Add the tics.
        dy = 30
        x00, y01 = (-width / 2, y00 + 10)
        self.shapes.append(Rectangle(x00 - gap / 4, y01, x00 + gap / 4, y01 + dy))
        x00 = -width / 6
        self.shapes.append(Rectangle(x00 - gap / 4, y01, x00 + gap / 4, y01 + dy))
        x00 = width / 6
        self.shapes.append(Rectangle(x00 - gap / 4, y01, x00 + gap / 4, y01 + dy))
        x00 = width / 2
        self.shapes.append(Rectangle(x00 - gap / 4, y01, x00 + gap / 4, y01 + dy))

        # Add the Supporters - Moderates - Opposers text.
        x01, y01 = (-width / 6 - width / 6, y00 + 35)
        self.shapes.append(Text('Supporters', x=x01, y=y01, size=30, bold=True))
        x01 = 0
        self.shapes.append(Text('Moderates', x=x01, y=y01, size=30, bold=True))
        x01 = width / 6 + width / 6
        self.shapes.append(Text('Opposers', x=x01, y=y01, size=30, bold=True))

    def create_ledgend02(self):
        """Create the ledge for the graph."""
        # Setup
        width = self.config['width']
        height = self.config['height']
        gap = self.config['gap']

        # Construct the bottom boarder.
        y00 = height
        self.shapes.append(
            Rectangle(-width / 2 - 40, y00, width / 2 + 40, y00 + 3, colour=Colour.BLACK))

        # Add the true tic.
        x00 = -width / 2
        self.shapes.append(Text('100', x=x00, y=y00 + 50, colour=Colour.BLACK, bold=True))
        self.shapes.append(
            Text('%', x=x00 + 22, y=y00 + 50, colour=Colour.BLACK, bold=True, align='start'))
        self.shapes.append(
            Rectangle(x00 - gap / 2, y00 + 7, x00 + gap / 2, y00 + 15, colour=Colour.BLACK))

        # Add the mid tic.
        x00 = 0
        self.shapes.append(
            Text('50', x=x00 - 10, y=y00 + 50, colour=Colour.BLACK, bold=True, align='end'))
        self.shapes.append(
            Text('/', x=x00, y=y00 + 50, colour=Colour.BLACK, bold=True, align='middle'))
        self.shapes.append(
            Text('50', x=x00 + 10, y=y00 + 50, colour=Colour.RED, bold=True, align='start'))
        self.shapes.append(
            Text('%', x=x00 + 40, y=y00 + 50, colour=Colour.RED, bold=True, align='start'))
        self.shapes.append(
            Rectangle(x00 - gap / 2, y00 + 7, x00 + gap / 2, y00 + 15, colour=Colour.BLACK))

        # Add the false tic.
        x00 = width / 2
        self.shapes.append(Text('100', x=x00, y=y00 + 50, colour=Colour.RED, bold=True))
        self.shapes.append(
            Text('%', x=x00 + 22, y=y00 + 50, colour=Colour.RED, bold=True, align='start'))
        self.shapes.append(
            Rectangle(x00 - gap / 2, y00 + 7, x00 + gap / 2, y00 + 15, colour=Colour.BLACK))

        # Add the True and False text.
        x01, y01 = (-width / 2 - 100, height)
        self.shapes.append(Text('True', x=x01, y=y01, size=40, colour=Colour.BLACK, bold=True))
        self.shapes.append(Text('False', x=-x01, y=y01, size=40, colour=Colour.RED, bold=True))

        # Add the Supporters - Moderates - Opposers text.
        x01, y01 = (-width / 6 - width / 6, y00 + 90)
        self.shapes.append(Text('Supporters', x=x01, y=y01, size=30, bold=True))
        x01 = 0
        self.shapes.append(Text('Moderates', x=x01, y=y01, size=30, bold=True))
        x01 = width / 6 + width / 6
        self.shapes.append(Text('Opposers', x=x01, y=y01, size=30, bold=True))

        # Add tics.
        x01 = -width / 2
        self.shapes.append(
            Rectangle(x01 - gap / 4, y01 - 15, x01 + gap / 4, y01, colour=Colour.BLACK))
        x01 = -width / 6
        self.shapes.append(
            Rectangle(x01 - gap / 4, y01 - 15, x01 + gap / 4, y01, colour=Colour.BLACK))
        x01 = width / 6
        self.shapes.append(
            Rectangle(x01 - gap / 4, y01 - 15, x01 + gap / 4, y01, colour=Colour.BLACK))
        x01 = width / 2
        self.shapes.append(
            Rectangle(x01 - gap / 4, y01 - 15, x01 + gap / 4, y01, colour=Colour.BLACK))

    def get_svg(self):
        """Output the svg code for diagram.

        Returns:
            str: The svg code for displaying the diagram.
        """
        # Setup
        offset = {'x': 0, 'y': -self.boarder['top']}
        width = self.config['width'] + self.boarder['left'] + self.boarder['right']
        height = self.config['height'] + self.boarder['top'] + self.boarder['bottom']
        svg = """<center><svg baseProfile="full" version="1.1" viewBox="%d %d %d %d">
               """ % (-width / 2 + offset['x'], offset['y'], width, height)
        svg += """<defs>
                    <pattern id="hatch" patternUnits="userSpaceOnUse" patternTransform="rotate(45 0 0)" width="15" height="15">
                      <path d="M 0,0 L 15,0 M 0,0 L 0,15 Z" style="stroke:white; stroke-width:6.0" />
                    </pattern>
                  </defs>
               """
        for shape in self.shapes:
            svg += shape.get_svg()
        svg += """</svg></center>"""
        return svg

    def get_caption(self):
        """Dummy method, there is no caption for this diagram.

        Returns:
            str: Blank.
        """
        return ''


class OpinionBarGraph(BarGraph):
    """A class for drawing opinion bar graphs."""

    def __init__(self, opinion):
        """Create a bar graph for visualizing the point distribution awarded to a theory.

        Args:
            opinion (Opinion): The users opinion.
        """
        self.opinion = opinion
        self.content = opinion.content
        self.opinions = self.content.get_opinions()

        bins = min(24, max(6, 6 * (math.floor(self.opinions.count() / 18) - 1)))
        data00 = [0.5 - x.true_points() for x in self.opinions]
        data01 = numpy.histogram(data00, bins=bins, range=(-0.5, 0.5))
        super().__init__(data01)

    def construct(self):
        """Construct the diagram."""
        self.create_graph()
        self.create_hidden()
        self.create_ledgend()

    def create_hidden(self, opinion=None, tag_id='user01'):
        """Create the hidden shapes that highlight opinion.

        Args:
            opinion (Opinion, optional): The user's opinion. Defaults to None.
            tag_id (str, optional): The html tag to enable/disable visability (hide).
                Defaults to 'user01'.
        """
        width = self.config['width']
        height = self.config['height']
        y00 = self.config['height']
        gap = self.config['gap']
        max_h = max(self.data[0])

        if opinion is None:
            opinion = self.opinion

        true00, true01 = opinion.get_point_range()
        x00_true = -true00 + 0.5
        x01_true = -true01 + 0.5

        hidden_group01 = Group(tag_id=tag_id, hidden=True)
        for i, h in enumerate(self.data[0]):
            if h > 0:
                x00 = self.data[1][i]
                x01 = self.data[1][i + 1]
                if (x00 <= x00_true and x01_true <= x01) or (x00_true <= x00 and x01 <= x01_true):
                    hidden_group01.add(
                        Rectangle(
                            x00 * width + gap,
                            y00,
                            x01 * width - gap,
                            y00 - h / max_h * height,
                            hatch=True,
                            stroke_width=2.0,
                            stroke_colour=Colour.NONE,
                        ))
        self.shapes.append(hidden_group01)

    def get_caption(self):
        """Output caption text for diagram.

        Returns:
            str: The caption text for the diagram.
        """
        text = """The above histogram shows the true/false belief distribution
                   of the <b>%d</b> %s (the most left column captures the
                   opinions that allocated 100&#37; of their points to the truth
                   of the theory). Hover the mouse below to highlight the bin
                   that the opinion falls into.
                """ % (self.opinions.count(),
                       'opinion' if self.opinions.count() <= 1 else 'different opinions')
        text += '<br></br>'
        text += '<center>'
        text += '  <a tag_id="user01" href="#"> Highlight %s </a>' % self.opinion.get_owner()
        text += '</center>'
        return text


class OpinionComparisionBarGraph(OpinionBarGraph):
    """A class for drawing comparison bar graphs (two highlight opinions)."""

    def __init__(self, opinion01, opinion02):
        """Constructor for the OpinionComparisionBarGraph class.

        Args:
            opinion01 (Opinion): User01's opinion.
            opinion02 (Opinion): User02's opinion.
        """
        self.opinion01 = opinion01
        self.opinion02 = opinion02
        super().__init__(opinion01)

    def construct(self):
        """Construct the diagram."""
        self.create_graph()
        self.create_hidden(self.opinion01, tag_id='user01')
        self.create_hidden(self.opinion02, tag_id='user02')
        self.create_ledgend()

    def get_caption(self):
        """Output caption text for diagram.

        Returns:
            str: The caption text for the diagram.
        """
        text = """The above histogram shows the true/false belief distribution
                   of the <b>%d</b> %s (the most left column captures the
                   opinions that allocated 100&#37; of their points to the truth
                   of the theory). Hover the mouse below to highlight the bin
                   that the opinions falls into.
                """ % (
            self.opinions.count(),
            'opinion' if self.opinions.count() <= 1 else 'different opinions',
        )
        text += '<br></br>'
        text += '<div class="row">'
        text += '<div class="col-6 text-center">'
        text += ' <a tag_id="user01" href="#"> Highlight %s </a>' % self.opinion01.get_owner()
        text += '</div>'
        text += '<div class="col-6 text-center">'
        text += ' <a tag_id="user02" href="#"> Highlight %s </a>' % self.opinion02.get_owner()
        text += '</div>'
        text += '</div>'
        return text


class DemoBarGraph(BarGraph):
    """A class for drawing demo bar graphs (fake data)."""

    def __init__(self):
        """Constructor for the DemoBarGraph class."""
        total = 0.0
        data = [[], [-0.5]]
        resolution = 18
        for i in range(resolution):
            x01 = -0.5 + 1.0 * (i + 1) / resolution
            y00 = random.random()
            data[0].append(y00)
            data[1].append(x01)
            total += y00
        for i in range(resolution):
            data[0][i] = data[0][i] / total
        super().__init__(data)


# *******************************************************************************
# main (used for testing)
# *******************************************************************************
if __name__ == "__main__":
    pass
