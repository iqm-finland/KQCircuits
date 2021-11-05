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


from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.pya_resolver import pya
from kqcircuits.test_structures.test_structure import TestStructure
from kqcircuits.util.parameters import Param, pdt


class AirbridgeDC(TestStructure):
    """The PCell declaration for an airbridge test structure for four-point DC measurements."""

    n_ab = Param(pdt.TypeInt, "Number of airbridges", 30)
    pad_height = Param(pdt.TypeDouble, "Pad height", 500, unit="μm")
    width = Param(pdt.TypeDouble, "Total width", 2000, unit="μm")

    def build(self):

        # create airbridges and islands through which they are connected

        cell_ab = self.add_element(Airbridge, airbridge_type="Airbridge Rectangular")

        ab_params = cell_ab.pcell_parameters_by_name()
        bridge_width = ab_params["bridge_width"]
        ab_pad_extra = ab_params["pad_extra"]
        ab_pad_width = ab_params["pad_length"] - 2 * ab_pad_extra
        ab_pad_length = ab_params["pad_length"] - 2 * ab_pad_extra
        bridge_length = ab_params["bridge_length"] + 2 * ab_pad_extra

        island_margin = 5  # how much an island extends beyond airbridge pads
        island_width = bridge_width + ab_pad_extra*2 + 2*island_margin
        airbridge_separation = 30
        island_height = max(2*(ab_pad_length + ab_pad_width/2), 2*(ab_pad_width+ab_pad_extra)) + airbridge_separation\
                        + island_margin*2
        island = pya.DPolygon([
            pya.DPoint(0, 0),
            pya.DPoint(0, island_height),
            pya.DPoint(island_width, island_height),
            pya.DPoint(island_width, 0),
        ])

        islands_region = pya.Region()

        x_step = island_width + bridge_length
        y_step = island_height + bridge_length

        pad_spacing_y = 150

        # The airbridges are created from left to right, by "snaking" in such a way that minimal horizontal space is
        # used, while keeping within the vertical extents of the pads.

        n_ab_placed = 0
        n_ab_remaining = self.n_ab
        n_ab_horizontal = 0
        # The ab_type here depends the position and direction of the airbridge:
        # "bottom" and "top" for horizontal airbridges at top or bottom of a vertical sequence of airbridges
        # "up" and "down" for vertical airbridges depending on which direction the airbridge is compared to previous one
        ab_type = "bottom"
        x = 0
        y = 0
        row = 0

        while n_ab_remaining > 0:

            if ab_type == "bottom":
                ab_trans = pya.DTrans(1, False, x + (island_width + x_step)/2,
                                      y + island_margin + ab_pad_width/2 + ab_pad_extra)
                x += x_step
                if row == 0 and n_ab_remaining < 5:
                    ab_type = "top"
                else:
                    ab_type = "up"
                n_ab_horizontal += 1
            elif ab_type == "up":
                ab_trans = pya.DTrans(0, False, x + island_width/2,
                                      y + island_height + (y_step - island_height)/2)
                y += y_step
                row += 1
                if y + 2*island_height + bridge_length > pad_spacing_y/2 + self.pad_height + island_height/2 or \
                   (row >= 0 and (n_ab_remaining <= row + 4 or n_ab_remaining == row + 6)):
                    ab_type = "top"
            elif ab_type == "top":
                ab_trans = pya.DTrans(1, False, x + (island_width + x_step)/2,
                                      y + island_height - island_margin - ab_pad_width/2 - ab_pad_extra)
                x += x_step
                if row == 0 and n_ab_remaining < 5:
                    ab_type = "bottom"
                else:
                    ab_type = "down"
                n_ab_horizontal += 1
            else:  # ab_type == "down"
                ab_trans = pya.DTrans(0, False, x + island_width/2, y - (y_step - island_height)/2)
                y -= y_step
                row -= 1
                if y - island_height - bridge_length < -pad_spacing_y/2 - self.pad_height + island_height/2 or \
                   (row < 0 and (n_ab_remaining <= -row + 4 or n_ab_remaining == -row + 6)) or \
                   (row == 0 and n_ab_remaining < 5):
                    ab_type = "bottom"

            self.insert_cell(cell_ab, ab_trans)

            if n_ab_remaining > 1:
                island_trans = pya.DTrans(pya.DVector(x, y))
                islands_region.insert((island_trans*island).to_itype(self.layout.dbu))

            n_ab_placed += 1
            n_ab_remaining -= 1

        pad_spacing_x = n_ab_horizontal*(bridge_length + island_width) - island_width

        # once all the airbridges and islands have been created, transform them so that they are centered around (0, 0)
        islands_trans = pya.DTrans(pya.DVector(-pad_spacing_x/2 - island_width, -island_height/2))
        islands_region.transform(islands_trans.to_itype(self.layout.dbu))
        for inst in self.cell.each_inst():
            inst.transform(islands_trans)

        # create pads
        pads_region = pya.Region()
        gap_extra = 50  # how much the gap layer extends beyond the pads
        pad_width = (self.width - pad_spacing_x)/2 - gap_extra
        self.produce_four_point_pads(pads_region, pad_width, self.pad_height, pad_spacing_x, pad_spacing_y, True,
                                     refpoint_distance=100)

        # combine pads and islands and create the metal gap region based on them
        metal_region = islands_region + pads_region
        self.produce_etched_region(metal_region, pya.DPoint(0, 0), 2*pad_width + pad_spacing_x + 2*gap_extra,
                                   2*self.pad_height + pad_spacing_y + 2*gap_extra)
