# geo-relations

"""
This package generates data for testing algorithms that are sensitive to
spatial relationships among objects. It contains these classes.

- `ShapeHarvester`: Download example shapes from OpenStreetMap.
- `RelationGenerator`: Generates pairs of shapes having prescribed relationships.

And it has this utility function:

- `draw_shape`: Add a shape to a `plotly` figure.
"""


__version__ = "0.0.1"
__author__ = "John B Collins"

from .harvesters import ShapeHarvester
from .generators import RelationGenerator
from .utilities import draw_shape
