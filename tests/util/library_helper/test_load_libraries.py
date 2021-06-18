# This code is part of KQCircuits
# Copyright (C) 2021 IQM Finland Oy
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not, see
# https://www.gnu.org/licenses/gpl-3.0.html.
#
# The software distribution should follow IQM trademark policy for open-source software
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).


import logging
import pytest

import klayout.db as pya

from kqcircuits.util.library_helper import load_libraries

log = logging.getLogger(__name__)


def test_load():
    libraries = load_libraries(path="elements")
    pcells = [name for library in libraries.values() for name in library.layout().pcell_names()]
    assert "Airbridge Rectangular" in pcells


@pytest.mark.skip(reason="It does not work with KLayout 0.27.")
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
