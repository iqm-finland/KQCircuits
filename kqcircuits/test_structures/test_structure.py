import sys
from importlib import reload
from autologging import logged, traced

from kqcircuits.elements.element import Element
from kqcircuits.util.library_helper import LIBRARY_NAMES

reload(sys.modules[Element.__module__])


@logged
@traced
class TestStructure(Element):
    """Base PCell declaration for test structures.
    """

    LIBRARY_NAME = LIBRARY_NAMES["TestStructure"]
    LIBRARY_DESCRIPTION = "Superconducting quantum circuit library for test structures."

    PARAMETERS_SCHEMA = {}

    def __init__(self):
        super().__init__()
