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

from kqcircuits.pya_resolver import pya

from kqcircuits.util.library_helper import load_libraries, delete_library

log = logging.getLogger(__name__)


# normal cases

@pytest.mark.skip(reason="It does not work with KLayout 0.27.")
def test_delete():
    load_libraries(path="elements")
    assert "Element Library" in pya.Library.library_names()
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
