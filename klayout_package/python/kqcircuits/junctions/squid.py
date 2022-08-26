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

from kqcircuits.junctions.junction import Junction
from kqcircuits.util.parameters import Param, pdt


@logged
class Squid(Junction):
    """Base class for SQUIDs without actual produce function.

    This class can represent both code generated and manually designed SQUIDs. Thus, any SQUID can be created using code
    like

        `self.add_element(Squid, junction_type="SquidName", **parameters)`,

    where "SquidName" is either a specific squid class name or name of a manually designed squid cell.
    """

    loop_area = Param(pdt.TypeDouble, "Loop area", 100, unit="μm^2")
