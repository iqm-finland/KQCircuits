import logging

import klayout.db as pya

from kqcircuits.util.library_helper import load_all_libraries

log = logging.getLogger(__name__)


def test_load_all():
    result = load_all_libraries()
    assert len(result) == 3
    assert "Element Library" in pya.Library.library_names()
    assert "Chip Library" in pya.Library.library_names()
    assert "Test Structure Library" in pya.Library.library_names()
