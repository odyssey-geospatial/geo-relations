# geo-relations

"""
This package generates data for testing algorithms that are sensitive to
spatial relationships among objects. It contains these classes.

- `OSMShapeCollector`: Gather example shapes from OpenStreetMap.
- `RelationGenerator`: Generates pairs of shapes having prescribed relationships.

And it has this utility function:

- `draw_shape`: Add a shape to a `plotly` figure.
"""


__version__ = "1.0.2"
__author__ = "John B Collins"

from .collectors import OSMShapeCollector
from .generators import RelationGenerator
from .utilities import draw_shape
