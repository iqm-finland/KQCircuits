# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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
from dataclasses import dataclass
from copy import deepcopy

try:
    # Python 3.14+
    from annotationlib import Format, get_annotations

    def _class_annotations(cls):
        return get_annotations(cls, format=Format.FORWARDREF)

except ImportError:
    # Python 3.11–3.13
    from inspect import get_annotations

    def _class_annotations(cls):
        return get_annotations(cls, eval_str=False)


@dataclass(kw_only=True, frozen=True)
class Solution:
    """A Base class for both Elmer and Ansys Solution parameters

    Args:
        name: Name of the solution
    """

    name: str = ""

    def get_parameters(self):
        """Returns class parameters (also ClassVar parameters) in dictionary form"""
        return {
            **{k: getattr(self, k) for k in _class_annotations(type(self)).keys()},
            **self.__dict__,
        }

    def updated(self, **parameters):
        """Returns a modified copy of the Solution object"""
        p_dict = deepcopy(self.__dict__)
        p_dict.update(**parameters)
        return self.__class__(**p_dict)
