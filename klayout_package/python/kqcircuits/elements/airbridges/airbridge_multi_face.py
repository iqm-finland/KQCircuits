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


from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.flip_chip_connectors.flip_chip_connector_dc import FlipChipConnectorDc
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from


@add_parameters_from(FlipChipConnectorDc)
@add_parameters_from(Airbridge, bridge_width=40, pad_length=40)
class AirbridgeMultiFace(Airbridge):
    """PCell declaration for a multi-face equivalent for an airbridge.

    Origin is at the geometric center. The airbridge is in vertical direction.

    Adds base metal on the second face and optionally creates bumps at both ends.

    .. MARKERS_FOR_PNG 6,0 0,3 0,42 15.5,41.984755
    """

    default_type = "Airbridge Multi Face"
    include_bumps = Param(pdt.TypeBoolean, "Include bumps", True)

    def build(self):
        half_length = self.bridge_length / 2
        half_box_length = half_length + self.pad_length
        half_width = self.bridge_width / 2

        # Add base metal addition to second face
        shape = pya.DBox(-half_width, -half_box_length, half_width, half_box_length)
        self.cell.shapes(self.get_layer("base_metal_addition", 1)).insert(shape)

        # Add ground grid avoidance to second face
        self.add_protection(shape.enlarged(self.margin, self.margin), 1)

        # Flip-chip bump
        if self.include_bumps:
            bump_dist = half_length + self.pad_length / 2
            bump = self.add_element(FlipChipConnectorDc)
            self.insert_cell(bump, pya.DTrans(pya.DPoint(0.0, bump_dist)))
            self.insert_cell(bump, pya.DTrans(pya.DPoint(0.0, -bump_dist)))

        # refpoints for connecting to waveguides
        self.add_port("a", pya.DPoint(0, half_length), pya.DVector(0, 1))
        self.add_port("b", pya.DPoint(0, -half_length), pya.DVector(0, -1))
