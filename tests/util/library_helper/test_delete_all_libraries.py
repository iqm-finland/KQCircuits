import logging

import klayout.db as pya

from kqcircuits.util.library_helper import load_all_libraries, delete_all_libraries

log = logging.getLogger(__name__)


def test_delete_all():
    load_all_libraries()
    assert len(pya.Library.library_names()) > 1
    delete_all_libraries()
    assert pya.Library.library_names() == ["Basic"]
