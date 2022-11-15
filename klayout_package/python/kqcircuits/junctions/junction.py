# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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


from autologging import logged

from kqcircuits.elements.element import Element
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.defaults import default_junction_type
from kqcircuits.junctions import junction_type_choices


@logged
class Junction(Element):
    """Base class for junctions without actual produce function.

    This class can represent both code generated and manually designed junctions. Thus, any junction
    can be created using code like

        `self.add_element(Junction, junction_type="JunctionName", **parameters)`,

    where "JunctionName" is either a specific junction class name or name of a manually designed
    junction cell.
    """

    LIBRARY_NAME = "Junction Library"
    LIBRARY_DESCRIPTION = "Library for junctions."
    LIBRARY_PATH = "junctions"

    default_type = default_junction_type

    junction_type = Param(pdt.TypeString, "Junction Type", default_junction_type, choices=junction_type_choices)
    junction_width = Param(pdt.TypeDouble, "Junction width for code generated element", 0.02, unit="μm",
                           docstring="Junction width (only used for code generated element)")
    junction_parameters = Param(pdt.TypeString, "Extra Junction Parameters", "{}")
    _junction_parameters = Param(pdt.TypeString, "Previous state of *_parameters", "{}", hidden=True)

    @classmethod
    def create(cls, layout, library=None, junction_type=None, **parameters):
        """Create cell for a junction in layout."""
        return cls.create_subtype(layout, library, junction_type, **parameters)[0]

    def coerce_parameters_impl(self):
        self.sync_parameters(Junction)
