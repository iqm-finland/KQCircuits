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

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.junctions.junction import Junction


@logged
class NoSquid(Junction):
    """The PCell declaration for a No SQUID junction.

    Origin at the center of junction layer bottom edge.
    """

    junction_total_length = Param(pdt.TypeDouble, "Junction total length", 26.5, unit='µm')

    def build(self):
        # only add refpoints
        self.refpoints["origin_squid"] = pya.DPoint(0, 0)
        self.refpoints["port_common"] = pya.DPoint(0, self.junction_total_length)
