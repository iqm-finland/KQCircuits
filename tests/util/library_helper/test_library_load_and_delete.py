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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


import logging

from kqcircuits.pya_resolver import pya

from kqcircuits.util.library_helper import load_libraries, delete_library, delete_all_libraries

log = logging.getLogger(__name__)


# normal cases


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
    assert "Deleted all libraries." in caplog.text
    assert "Reloaded module 'airbridge_rectangular'." in caplog.text
    caplog.set_level(level)


def test_load_all():
    result = load_libraries()
    assert len(result) >= 4
    assert "Element Library" in pya.Library.library_names()
    assert "Chip Library" in pya.Library.library_names()
    assert "Test Structure Library" in pya.Library.library_names()
    assert "Junction Library" in pya.Library.library_names()


def test_delete_all():
    load_libraries()
    assert len(pya.Library.library_names()) > 1
    delete_all_libraries()
    assert pya.Library.library_names() == ["Basic"]


def test_delete():
    delete_library("Chip Library")
    load_libraries(path="elements")
    assert "Element Library" in pya.Library.library_names()
    assert "Chip Library" not in pya.Library.library_names()
    delete_library("Element Library")
    assert "Element Library" not in pya.Library.library_names()


# edge cases


def test_without_input():
    load_libraries()
    before_count = len(pya.Library.library_names())
    delete_library()
    after_count = len(pya.Library.library_names())
    assert before_count == after_count


def test_none():
    load_libraries()
    before_count = len(pya.Library.library_names())
    delete_library(None)
    after_count = len(pya.Library.library_names())
    assert before_count == after_count


def test_invalid_name():
    load_libraries()
    before_count = len(pya.Library.library_names())
    delete_library("foo")
    after_count = len(pya.Library.library_names())
    assert before_count == after_count
