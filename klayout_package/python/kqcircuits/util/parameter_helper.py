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

"""
    Helper module for pcell parameter schemas.

    Typical usage example::

        from kqcircuits.util.parameter_helper import Validator
        schema = {
            "n": {
                "type": pya.PCellParameterDeclaration.TypeInt,
                "description": "Number of elements",
                "default": 10
            }
        }
        validator = Validator(schema)
        if validator.validate({"n": 100}):
            # Do something with validated parameters...
"""

from autologging import logged

from kqcircuits.pya_resolver import pya


def normalize_rules(name, rules):
    """Normalizes rule fields corresponding to specified name.

    Adds missing optional rule fields with default settings.

    Returns:
        Dictionary containing all rule fields.
    """
    return {
        "name": name,
        "type": rules["type"],
        "description": rules["description"],
        "hidden": _get_rule("hidden", False, rules),
        "readonly": _get_rule("readonly", False, rules),
        "unit": _get_rule("unit", None, rules),
        "default": _get_rule("default", None, rules),
        "choices": _get_rule("choices", None, rules),
        "required": _get_rule("required", False, rules)
    }


@logged
class Validator():
    """Validates KLayout parameters according to specified schema.

    Attributes:
        schema: Dictionary containing rules for validating KLayout parameters.
    """

    def __init__(self, schema):
        self.schema = schema
        self.__validate_schema()

    def validate(self, parameters):
        """Validates KLayout parameters.

        Args:
            parameters: KLayout parameters.

        Returns:
            True if validation is successful.

        Raises:
            MissingParameterException: Failed to validate because a required parameter is missing.
            InvalidParameterException: Failed to validate parameter because of invalid value.
        """
        for name, rules in self.schema.items():
            rules = normalize_rules(name, rules)
            self.__log.debug("Validating {} using rules [{}].".format(name, rules))
            if name in parameters:
                value = parameters[name]
                if value is None:
                    if rules["required"]:
                        raise ValueError(_generate_missing_parameter_message(name))
                    self.__log.debug("Validated {}.".format(name))
                    return True
                else:
                    if _is_of_type(value, rules["type"]):
                        self.__log.debug("Validated {}.".format(name))
                        return True
                    else:
                        raise ValueError(_generate_invalid_parameter_message(name, value))
            else:
                if rules["required"]:
                    raise ValueError(_generate_missing_parameter_message(name))
                self.__log.debug("Validated {}.".format(name))
                return True

    def __validate_schema(self):
        """Validates schema.

        Returns:
            True if validation is successful.

        Raises:
            MissingRuleFieldException: Failed to validate schema because a required rule field is missing.
            InvalidRuleValueException: Failed to validate schema because of invalid rule value.
        """
        for name, rules in self.schema.items():
            if "type" not in rules:
                raise ValueError(_generate_missing_rule_message(name, "type"))
            if "type" in rules and not _is_valid_type(rules["type"]):
                raise ValueError(_generate_invalid_rule_message(name, "type", rules["type"]))
            if "description" not in rules:
                raise ValueError(_generate_missing_rule_message(name, "description"))
            if "description" in rules and not isinstance(rules["description"], str):
                raise ValueError(_generate_invalid_rule_message(name, "description", rules["description"]))
            if "hidden" in rules and not isinstance(rules["hidden"], bool):
                raise ValueError(_generate_invalid_rule_message(name, "hidden", rules["hidden"]))
            if "readonly" in rules and not isinstance(rules["readonly"], bool):
                raise ValueError(_generate_invalid_rule_message(name, "readonly", rules["readonly"]))
            if "unit" in rules and not isinstance(rules["unit"], str):
                raise ValueError(_generate_invalid_rule_message(name, "unit", rules["unit"]))
            if "default" in rules and not _is_of_type(rules["default"], rules["type"]):
                raise ValueError(_generate_invalid_rule_message(name, "default", rules["default"]))
            if "choices" in rules and not _is_valid_choices(rules["choices"], rules["type"]):
                raise ValueError(_generate_invalid_rule_message(name, "choices", rules["choices"]))
            if "required" in rules and not isinstance(rules["required"], bool):
                raise ValueError(_generate_invalid_rule_message(name, "required", rules["required"]))
            return True


# ********************************************************************************
# PRIVATE METHODS
# ********************************************************************************


def _get_rule(name, default, rules):
    """Get rule from dictionary without raising exception.

    Args:
        name: Rule name.
        default: Default rule value.
        rules: Rules dictionary.

    Returns:
        Dictionary containing rule.
    """
    if name in rules:
        return rules[name]
    else:
        return default


def _is_valid_type(value):
    """Check if value is a KLayout parameter type.

    Args:
        value: Type value.

    Returns:
        True if value is of a Klayout parameter type.
    """
    return value is pya.PCellParameterDeclaration.TypeBoolean \
        or value is pya.PCellParameterDeclaration.TypeDouble \
        or value is pya.PCellParameterDeclaration.TypeInt \
        or value is pya.PCellParameterDeclaration.TypeLayer \
        or value is pya.PCellParameterDeclaration.TypeList \
        or value is pya.PCellParameterDeclaration.TypeNone \
        or value is pya.PCellParameterDeclaration.TypeShape \
        or value is pya.PCellParameterDeclaration.TypeString


def _is_of_type(value, rule_type):
    """Check if value is a KLayout parameter type.

    Args:
        value: Rule value.
        rule_type: Rule type.

    Returns:
        True if value is compatible with specified Klayout parameter type.
    """
    if rule_type is pya.PCellParameterDeclaration.TypeBoolean and isinstance(value, bool):
        return True
    if rule_type is pya.PCellParameterDeclaration.TypeDouble and _is_float(value):
        return True
    if rule_type is pya.PCellParameterDeclaration.TypeInt and isinstance(value, int):
        return True
    if rule_type is pya.PCellParameterDeclaration.TypeLayer and isinstance(value, pya.LayerInfo):
        return True
    if rule_type is pya.PCellParameterDeclaration.TypeList and isinstance(value, list):
        return True
    if rule_type is pya.PCellParameterDeclaration.TypeNone and value is None:
        return True
    if rule_type is pya.PCellParameterDeclaration.TypeShape and (
            isinstance(value, (pya.DBox, pya.DEdge, pya.DPoint, pya.DPolygon, pya.DPath))
    ):
        return True
    if rule_type is pya.PCellParameterDeclaration.TypeString and isinstance(value, str):
        return True

    return False


def _is_valid_choices(value, choice_type):
    """Validate choices.

    Args:
        value: Choices.
        choice_type: Choice type.

    Returns:
        True if valid choices.
    """
    return isinstance(value, list) and value and _is_valid_choice(value, choice_type)


def _is_valid_choice(value, choice_type):
    """Validate choice type.

    Args:
        value: Choice value.
        choice_type: Choice type.

    Returns:
        True if value is valid choice type.
    """
    return (isinstance(value, list)
            and value
            and len(value) == 2
            and value[0] is not None
            and value[1] is not None
            and isinstance(value[0], str)
            and isinstance(value[1], choice_type))


def _is_float(value):
    """Check if valid float.

    Args:
        value: Number value.

    Returns:
        True if value is valid float.
    """
    return (isinstance(value, float)
            or (isinstance(value, int) and value == int(float(value))))


def _generate_missing_rule_message(rule_name, key):
    """Generate missing rule error message.

    Returns:
        Message string.
    """
    return "Missing required key [{}] in schema rule [{}].".format(key, rule_name)


def _generate_invalid_rule_message(rule_name, key, value):
    """Generate missing rule error message.

    Returns:
        Message string.
    """
    return "Invalid value [{}] for [{}] in schema rule [{}].".format(value, key, rule_name)


def _generate_missing_parameter_message(parameter_name):
    """Generate missing rule error message.

    Returns:
        Message string.
    """
    return "Missing required value for parameter [{}].".format(parameter_name)


def _generate_invalid_parameter_message(parameter_name, value):
    """Generate missing rule error message.

    Returns:
        Message string.
    """
    return "Invalid value [{}] specified for parameter [{}].".format(value, parameter_name)
