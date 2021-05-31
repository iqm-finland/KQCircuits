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

from kqcircuits.util.parameter_helper import Validator

log = logging.getLogger(__name__)


# normal cases

def test_type_boolean():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Test rule for TypeBoolean."
        }
    }
    validator = Validator(schema)
    result = validator.validate({"test": True})
    assert result is True


def test_type_double():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Test rule for TypeDouble."
        }
    }
    validator = Validator(schema)
    result = validator.validate({"test": 3.14})
    assert result is True


def test_type_int():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Test rule for TypeInt."
        }
    }
    validator = Validator(schema)
    result = validator.validate({"test": 123})
    assert result is True


def test_type_layer():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeLayer,
            "description": "Test rule for TypeLayer."
        }
    }
    validator = Validator(schema)
    result = validator.validate({"test": pya.LayerInfo(1, 0, "test")})
    assert result is True


def test_type_list():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Test rule for TypeList."
        }
    }
    validator = Validator(schema)
    result = validator.validate({"test": ["test", 3.14, True]})
    assert result is True


def test_type_none():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeNone,
            "description": "Test rule for TypeNone."
        }
    }
    validator = Validator(schema)
    result = validator.validate({"test": None})
    assert result is True


def test_type_shape():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeShape,
            "description": "Test rule for TypeShape."
        }
    }
    validator = Validator(schema)
    result = validator.validate({"test": pya.DPoint(1, 1)})
    assert result is True


def test_type_string():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Test rule for TypeString."
        }
    }
    validator = Validator(schema)
    result = validator.validate({"test": "test"})
    assert result is True


# edge cases

def test_invalid_parameter():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Test rule for TypeInt."
        }
    }
    validator = Validator(schema)
    with pytest.raises(ValueError) as info:
        validator.validate({"test": "INVALID"})
    assert str(info.value) == "Invalid value [INVALID] specified for parameter [test]."


def test_missing_parameter():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Test rule for TypeInt."
        }
    }
    validator = Validator(schema)
    result = validator.validate({})
    assert result is True


def test_missing_required_parameter():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Test rule for TypeInt.",
            "required": True
        }
    }
    validator = Validator(schema)
    with pytest.raises(ValueError) as info:
        validator.validate({})
    assert str(info.value) == "Missing required value for parameter [test]."


def test_none_parameter():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Test rule for TypeInt."
        }
    }
    validator = Validator(schema)
    result = validator.validate({"test": None})
    assert result is True


def test_none_required_parameter():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Test rule for TypeInt.",
            "required": True
        }
    }
    validator = Validator(schema)
    with pytest.raises(ValueError) as info:
        validator.validate({"test": None})
    assert str(info.value) == "Missing required value for parameter [test]."


def test_schema_with_missing_type():
    schema = {
        "test": {
            "description": "Testing."
        }
    }
    with pytest.raises(ValueError) as info:
        Validator(schema)
    assert str(info.value) == "Missing required key [type] in schema rule [test]."


def test_schema_with_invalid_type():
    schema = {
        "test": {
            "type": int,
            "description": "Testing."
        }
    }
    with pytest.raises(ValueError) as info:
        Validator(schema)
    assert str(info.value) == "Invalid value [<class 'int'>] for [type] in schema rule [test]."


def test_schema_with_missing_description():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt
        }
    }
    with pytest.raises(ValueError) as info:
        Validator(schema)
    assert str(info.value) == "Missing required key [description] in schema rule [test]."


def test_schema_with_invalid_description():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": 3.14
        }
    }
    with pytest.raises(ValueError) as info:
        Validator(schema)
    assert str(info.value) == "Invalid value [3.14] for [description] in schema rule [test]."


def test_schema_with_invalid_hidden():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Test rule for TypeInt.",
            "hidden": "INVALID"
        }
    }
    with pytest.raises(ValueError) as info:
        Validator(schema)
    assert str(info.value) == "Invalid value [INVALID] for [hidden] in schema rule [test]."


def test_schema_with_invalid_readonly():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Test rule for TypeInt.",
            "readonly": "INVALID"
        }
    }
    with pytest.raises(ValueError) as info:
        Validator(schema)
    assert str(info.value) == "Invalid value [INVALID] for [readonly] in schema rule [test]."


def test_schema_with_invalid_unit():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Test rule for TypeInt.",
            "unit": 3.14
        }
    }
    with pytest.raises(ValueError) as info:
        Validator(schema)
    assert str(info.value) == "Invalid value [3.14] for [unit] in schema rule [test]."


def test_schema_with_invalid_default():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Test rule for TypeInt.",
            "default": "INVALID"
        }
    }
    with pytest.raises(ValueError) as info:
        Validator(schema)
    assert str(info.value) == "Invalid value [INVALID] for [default] in schema rule [test]."


def test_schema_with_invalid_choices():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Test rule for TypeInt.",
            "choices": "INVALID"
        }
    }
    with pytest.raises(ValueError) as info:
        Validator(schema)
    assert str(info.value) == "Invalid value [INVALID] for [choices] in schema rule [test]."


def test_schema_with_invalid_choices_item():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Test rule for TypeInt.",
            "choices": [1]
        }
    }
    with pytest.raises(ValueError) as info:
        Validator(schema)
    assert str(info.value) == "Invalid value [[1]] for [choices] in schema rule [test]."


def test_schema_with_invalid_choices_description():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Test rule for TypeInt.",
            "choices": [["1", 1], [2, 2]]
        }
    }
    with pytest.raises(ValueError) as info:
        Validator(schema)
    assert str(info.value) == "Invalid value [[['1', 1], [2, 2]]] for [choices] in schema rule [test]."


def test_schema_with_invalid_choices_type():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Test rule for TypeInt.",
            "choices": [["1", 1], ["2", "INVALID"]]
        }
    }
    with pytest.raises(ValueError) as info:
        Validator(schema)
    assert str(info.value) == "Invalid value [[['1', 1], ['2', 'INVALID']]] for [choices] in schema rule [test]."


def test_schema_with_invalid_required():
    schema = {
        "test": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Test rule for TypeInt.",
            "required": "INVALID"
        }
    }
    with pytest.raises(ValueError) as info:
        Validator(schema)
    assert str(info.value) == "Invalid value [INVALID] for [required] in schema rule [test]."
