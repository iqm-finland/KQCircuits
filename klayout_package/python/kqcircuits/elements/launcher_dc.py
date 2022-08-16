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


from kqcircuits.elements.element import Element
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt


class LauncherDC(Element):
    """The PCell declaration for a DC launcher for connecting wirebonds.

    .. MARKERS_FOR_PNG 0,0 80,0 -278,-70
    """

    width = Param(pdt.TypeDouble, "Pad width", 500, unit="μm")

    def build(self):

        extra_width = 100

        offset = self.width/2
        metal_region = pya.Region((pya.DBox(-offset, -offset, offset, offset)).to_itype(self.layout.dbu))

        offset = (self.width + extra_width)/2
        gap_region = pya.Region((pya.DBox(-offset, -offset, offset, offset)).to_itype(self.layout.dbu))
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(gap_region - metal_region)

        offset = (self.width + extra_width)/2 + self.margin
        shape = pya.Region((pya.DBox(-offset, -offset, offset, offset)).to_itype(self.layout.dbu))
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(shape)

        # add reference point
        self.add_port("", pya.DPoint(0, 0))
