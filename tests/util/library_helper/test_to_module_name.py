import logging

import pytest

from kqcircuits.util.library_helper import to_module_name

log = logging.getLogger(__name__)


# SINGLE WORD TESTS

# normal cases

def test_pascal_case():
    result = to_module_name("AbcXyz")
    assert result == "abc_xyz"


def test_pascal_case_with_single_uppercase_letter():
    result = to_module_name("ABcXyz")
    assert result == "abc_xyz"


def test_pascal_case_with_multiple_single_uppercase_letters():
    result = to_module_name("ABcXYz")
    assert result == "abc_xyz"


# edge cases

def test_camel_case():
    with pytest.raises(ValueError) as info:
        to_module_name("abcXyz")
    assert str(info.value) == "PEP8 compliant class name 'abcXyz' must be PascalCase without underscores."


def test_snake_case():
    with pytest.raises(ValueError) as info:
        to_module_name("abc_xyz")
    assert str(info.value) == "PEP8 compliant class name 'abc_xyz' must be PascalCase without underscores."


def test_kebab_case():
    with pytest.raises(ValueError) as info:
        to_module_name("abc-xyz")
    assert str(info.value) == "Cannot convert invalid Python class name 'abc-xyz' to library name."


def test_space():
    with pytest.raises(ValueError) as info:
        to_module_name("abc xyz")
    assert str(info.value) == "Cannot convert invalid Python class name 'abc xyz' to library name."


def test_mixed_case_word():
    result = to_module_name("ABcXyZ")
    assert result == "abc_xy_z"


def test_without_input():
    with pytest.raises(ValueError) as info:
        to_module_name()
    assert str(info.value) == "Cannot convert nil or non-string class name 'None' to library name."


def test_none():
    with pytest.raises(ValueError) as info:
        to_module_name(None)
    assert str(info.value) == "Cannot convert nil or non-string class name 'None' to library name."


def test_empty_string():
    with pytest.raises(ValueError) as info:
        to_module_name("")
    assert str(info.value) == "Cannot convert nil or non-string class name '' to library name."


def test_number():
    with pytest.raises(ValueError) as info:
        to_module_name(3.14)
    assert str(info.value) == "Cannot convert nil or non-string class name '3.14' to library name."


def test_boolean():
    with pytest.raises(ValueError) as info:
        to_module_name(True)
    assert str(info.value) == "Cannot convert nil or non-string class name 'True' to library name."


def test_list():
    with pytest.raises(ValueError) as info:
        to_module_name(["AbcXyz"])
    assert str(info.value) == "Cannot convert nil or non-string class name '['AbcXyz']' to library name."
