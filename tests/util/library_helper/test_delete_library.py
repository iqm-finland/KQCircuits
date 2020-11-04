# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import logging

from kqcircuits.pya_resolver import pya

from kqcircuits.util.library_helper import load_libraries, delete_library

log = logging.getLogger(__name__)


# normal cases

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
