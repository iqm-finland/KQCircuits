import logging

import klayout.db as pya

from kqcircuits.util.library_helper import load_all_libraries, load_library, delete_library

log = logging.getLogger(__name__)


# normal cases

def test_delete():
    load_library("Element Library")
    assert "Element Library" in pya.Library.library_names()
    delete_library("Element Library")
    assert "Element Library" not in pya.Library.library_names()


# edge cases

def test_without_input():
    load_all_libraries()
    before_count = len(pya.Library.library_names())
    delete_library()
    after_count = len(pya.Library.library_names())
    assert before_count == after_count


def test_none():
    load_all_libraries()
    before_count = len(pya.Library.library_names())
    delete_library(None)
    after_count = len(pya.Library.library_names())
    assert before_count == after_count


def test_invalid_name():
    load_all_libraries()
    before_count = len(pya.Library.library_names())
    delete_library("foo")
    after_count = len(pya.Library.library_names())
    assert before_count == after_count
