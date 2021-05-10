# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya

def add_parameters_from(cls, *args):
    """Decorator function to add parameters to the decorated class.

    If `args` is empty it takes all parameters of `cls`, otherwise only takes parameters mentioned
    in `args`. Only add parameters that are not already class attributes.

    Args:
        cls: the class to take parameters from
        args: is an optional list of parameter names to take
    """

    cp = {n: p for n, p in cls.get_schema(noparents=True).items() if not args or n in args}

    def _decorate(obj):
        for name, param in cp.items():
            if not hasattr(obj, name):
                setattr(obj, name, param)
                param.__set_name__(obj, name)
        return obj

    return lambda obj: _decorate(obj)


class pdt:
    """A namespace for pya.PCellParameterDeclaration types."""
    TypeDouble = pya.PCellParameterDeclaration.TypeDouble
    TypeInt = pya.PCellParameterDeclaration.TypeInt
    TypeList = pya.PCellParameterDeclaration.TypeList
    TypeString = pya.PCellParameterDeclaration.TypeString
    TypeNone = pya.PCellParameterDeclaration.TypeNone
    TypeShape = pya.PCellParameterDeclaration.TypeShape
    TypeBoolean = pya.PCellParameterDeclaration.TypeBoolean
    TypeLayer = pya.PCellParameterDeclaration.TypeLayer


class Param():
    """PCell parameters as Element class attributes.

    This should be used for defining PCell parameters in Element subclasses.
    """

    _index = {} # A private dictionary of parameter dictionaries indexed by owner classes

    @classmethod
    def get_all(cls, owner):
        """Get all parameters of given owner.

        Args:
            owner: get all parameters of this class

        Returns:
            a name-to-Param dictionary of all paramters of class `owner` or an empty one if it has none.
        """

        if owner in cls._index:
            return cls._index[owner]
        else:
            return {}

    def __init__(self, data_type, description, default, **kwargs):
        self.data_type = data_type
        self.description = description
        self.default = default
        self.kwargs = kwargs

    def __set_name__(self, owner, name):
        self.name = name
        if owner not in self._index:
            self._index[owner] = {}
        self._index[owner][name] = self

    def __get__(self, obj, objtype):
        if obj is None or not hasattr(obj, "_param_values") or obj._param_values is None:
            return self.default
        if hasattr(obj, "_param_value_map"):    # Element
           return obj._param_values[obj._param_value_map[self.name]]
        else:                                   # Simulation
           return obj._param_values[self.name]

    def __set__(self, obj, value):
        if not hasattr(obj, "_param_values") or obj._param_values is None:
            obj._param_values = {}
        if hasattr(obj, "_param_value_map"):
            obj._param_values[obj._param_value_map[self.name]] = value
        else:
            obj._param_values[self.name] = value
