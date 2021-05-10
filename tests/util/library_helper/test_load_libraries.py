# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import logging

import klayout.db as pya

from kqcircuits.util.library_helper import load_libraries

log = logging.getLogger(__name__)


def test_load():
    libraries = load_libraries(path="elements")
    pcells = [name for library in libraries.values() for name in library.layout().pcell_names()]
    assert "Airbridge Rectangular" in pcells


def test_load_with_flush(caplog):
    level = logging.root.level
    caplog.set_level(logging.DEBUG)
    libraries = load_libraries(flush=True, path="elements")
    pcells = [name for library in libraries.values() for name in library.layout().pcell_names()]
    assert "Airbridge Rectangular" in pcells
    assert "Successfully deleted library 'Element Library'." in caplog.text
    assert "Reloaded module 'airbridge_rectangular'." in caplog.text
    caplog.set_level(level)


def test_load_all():
    result = load_libraries()
    assert len(result) >= 4
    assert "Element Library" in pya.Library.library_names()
    assert "Chip Library" in pya.Library.library_names()
    assert "Test Structure Library" in pya.Library.library_names()
    assert "SQUID Library" in pya.Library.library_names()
