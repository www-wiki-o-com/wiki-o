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
import random

from theories.graphs.shapes import Colour, Rectangle, Polygon
from theories.models.statistics import Stats

# *******************************************************************************
# Diagrams
#
#
#
#
#
#
# *******************************************************************************


class Guage():
    """A class for drawing guages."""

    # Constants
    DEFAULT_CONFIG = {'height': 12, 'aspect_ratio': 1.5, 'stroke_width': 0.0}
    DEFAULT_BOARDER = {'top': 0, 'bottom': 0, 'left': 0, 'right': 0}

    def __init__(self, width, colour=Colour.BLACK, config=None, boarder=None):
        """Constructor for the Guage class.

        Args:
            data (dict('true_facts':float, 'true_other':float, 'false_facts':float,
                'false_other':float)): The set of data to be used for the pie chart.
            config (dict('radius':float, 'c_offset':float, 'gap':float), optional):
                The configuration. Defaults to None.
            boarder (dict('top':float, 'bottom':float, 'left':float', 'right':float), optional):
                The bounding box used to size the diagram. Defaults to None.
        """
        self.width = width
        if config is None:
            self.config = self.DEFAULT_CONFIG
        else:
            self.config = config
        if boarder is None:
            self.boarder = self.DEFAULT_BOARDER
        else:
            self.boarder = boarder

        y02 = 100 / self.config['aspect_ratio']
        self.shapes = []
        if colour == Colour.BLACK_AND_RED:
            path = [(100 - width, 0), (100 - width, y02), (100, 0)]
            self.shapes.append(
                Polygon(path, stroke_width=self.config['stroke_width'], colour=Colour.BLACK))
            path = [(100, 0), (100, y02), (100 - width, y02)]
            self.shapes.append(
                Polygon(path, stroke_width=self.config['stroke_width'], colour=Colour.RED))
        else:
            self.shapes.append(
                Rectangle(x01=100 - width,
                          y01=0,
                          x02=100,
                          y02=100 / self.config['aspect_ratio'],
                          stroke_width=self.config['stroke_width'],
                          colour=colour))

    def get_svg(self):
        """Output the svg code for the diagram.

        Returns:
            str: The svg code for displaying the diagram.
        """
        # Setup
        boarder = self.boarder
        width = (100 + boarder['left'] + boarder['right'])
        height = (100 / self.config['aspect_ratio'] + boarder['top'] + boarder['bottom'])
        # SVG
        svg = '<svg class="icon" baseProfile="full" version="1.1"'
        svg += ' width="%d" height="%d"' % (int(
            self.config['height'] * self.config['aspect_ratio']), self.config['height'])
        svg += ' viewBox="0 0 %d %d">' % (width, height)
        for shape in self.shapes:
            svg += shape.get_svg()
        svg += """</svg>"""
        return svg


class DependencyGuage(Guage):
    """A class for drawing guages."""
    BLACK_RED_THRESHOLD = 0.5  # 1.0 * 2 / 3

    def __init__(self, dependency, normalize=1.0):
        """Constructor for the Guage class.

        Args:
            data (dict('true_facts':float, 'true_other':float, 'false_facts':float,
                'false_other':float)): The set of data to be used for the pie chart.
            config (dict('radius':float, 'c_offset':float, 'gap':float), optional):
                The configuration. Defaults to None.
            boarder (dict('top':float, 'bottom':float, 'left':float', 'right':float), optional):
                The bounding box used to size the diagram. Defaults to None.
        """
        # Calculate width.
        true_points = abs(dependency.true_points())  # hack, shouldn't need abs (TODO, fix)
        false_points = abs(dependency.false_points())  # hack, shouldn't need abs (TODO, fix)
        total_points = true_points + false_points
        width = 100 * total_points
        if normalize > 0:
            width = width / normalize
        else:
            width = 0.0

        # Decide colour.
        if total_points < 0.000001:
            colour = Colour.NONE
        elif true_points / total_points >= self.BLACK_RED_THRESHOLD:
            colour = Colour.BLACK
        elif false_points / total_points >= self.BLACK_RED_THRESHOLD:
            colour = Colour.RED
        else:
            colour = Colour.BLACK_AND_RED

        # Graph
        super().__init__(width=width, colour=colour)


# *******************************************************************************
# main (used for testing)
# *******************************************************************************
if __name__ == "__main__":
    pass
