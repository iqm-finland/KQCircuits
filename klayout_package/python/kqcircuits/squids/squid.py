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


from autologging import logged

from kqcircuits.elements.element import Element
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.defaults import default_squid_type
from kqcircuits.squids import squid_type_choices


@logged
class Squid(Element):
    """Base class for SQUIDs without actual produce function.

    This class can represent both code generated and manually designed SQUIDs. Thus, any SQUID can be created using code
    like

        `self.add_element(Squid, squid_type="SquidName", **parameters)`,

    where "SquidName" is either a specific squid class name or name of a manually designed squid cell.
    """

    LIBRARY_NAME = "SQUID Library"
    LIBRARY_DESCRIPTION = "Library for SQUIDs."
    LIBRARY_PATH = "squids"

    default_type = default_squid_type

    squid_type = Param(pdt.TypeString, "SQUID Type", default_squid_type, choices=squid_type_choices)
    junction_width = Param(pdt.TypeDouble, "Junction width for code generated squids", 0.02, unit="μm",
                           docstring="Junction width (only used for code generated squids)")
    loop_area = Param(pdt.TypeDouble, "Loop area", 100, unit="μm^2")

    @classmethod
    def create(cls, layout, library=None, squid_type=None, **parameters):
        """Create cell for a squid in layout."""
        return cls.create_subtype(layout, library, squid_type, **parameters)[0]
