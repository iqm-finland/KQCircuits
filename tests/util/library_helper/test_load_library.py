import logging

import pytest

from kqcircuits.util.library_helper import load_library

log = logging.getLogger(__name__)


# normal cases

def test_load():
    result = load_library("Element Library")
    pcells = result.layout().pcell_names()
    assert "Airbridge" in pcells


def test_load_with_flush(caplog):
    level = logging.root.level
    caplog.set_level(logging.DEBUG)
    result = load_library("Element Library", flush=True)
    pcells = result.layout().pcell_names()
    assert "Airbridge" in pcells
    assert "Successfully deleted library 'Element Library'." in caplog.text
    assert "Reloaded module 'airbridge'." in caplog.text
    caplog.set_level(level)


# edge cases

def test_without_input():
    with pytest.raises(ValueError) as info:
        load_library()
    assert str(info.value) == "Missing library name."


def test_none():
    with pytest.raises(ValueError) as info:
        load_library(None)
    assert str(info.value) == "Missing library name."


def test_invalid_name():
    result = load_library("foo")
    assert result is None
