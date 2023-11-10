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


class TestStructure(Element):
    """Base PCell declaration for test structures."""

    LIBRARY_NAME = "Test Structure Library"
    LIBRARY_DESCRIPTION = "Superconducting quantum circuit library for test structures."
    LIBRARY_PATH = "test_structures"

    def produce_pad(self, x, y, pads_region, pad_width, pad_height):
        """Inserts a square pad shape to pads_region.

        Args:
            x: x-coordinate of the pad center
            y: y-coordinate of the pad center
            pads_region: Region to which the pad shape is inserted
            pad_width: width (and height) of the pad

        """
        offset_x = pad_width/2
        offset_y = pad_height/2
        pad = pya.DPolygon([
            pya.DPoint(x - offset_x, y - offset_y),
            pya.DPoint(x - offset_x, y + offset_y),
            pya.DPoint(x + offset_x, y + offset_y),
            pya.DPoint(x + offset_x, y - offset_y),
        ])
        pads_region.insert(pad.to_itype(self.layout.dbu))

    def produce_four_point_pads(self, pads_region, pad_width, pad_height, pad_spacing_x, pad_spacing_y, connect_pads,
                                trans=pya.DTrans(), refpoint_prefix="probe", refpoint_distance=None):
        """Inserts four pads to pads_region.

        Args:
            pads_region: Region to which the pad shapes are inserted
            pad_width: width (and height) of the pads
            pad_spacing_x: x-distance between the pads
            pad_spacing_y: y-distance between the pads
            connect_pads: Boolean determining if the two pads on each side are connected
            trans: transformation applied to the pads
            refpoint_prefix: prefix used for the refpoint names
            refpoint_distance: Horizontal distance of refpoints from closest outer edges.
                If None, the refpoints will be at the center of the pads.

        """

        pad_offset_x = (pad_spacing_x + pad_width)/2
        pad_offset_y = (pad_spacing_y + pad_height)/2

        pos_sw = pya.DPoint(trans.disp.x - pad_offset_x, trans.disp.y - pad_offset_y)
        pos_nw = pya.DPoint(trans.disp.x - pad_offset_x, trans.disp.y + pad_offset_y)
        pos_ne = pya.DPoint(trans.disp.x + pad_offset_x, trans.disp.y + pad_offset_y)
        pos_se = pya.DPoint(trans.disp.x + pad_offset_x, trans.disp.y - pad_offset_y)

        self.produce_pad(pos_sw.x, pos_sw.y, pads_region, pad_width, pad_height)
        self.produce_pad(pos_nw.x, pos_nw.y, pads_region, pad_width, pad_height)
        self.produce_pad(pos_ne.x, pos_ne.y, pads_region, pad_width, pad_height)
        self.produce_pad(pos_se.x, pos_se.y, pads_region, pad_width, pad_height)

        if connect_pads:
            pad_connection_box_width = 50
            pad_connection_box = pya.DBox(pya.DPoint(0, 0),
                                          pya.DPoint(pad_connection_box_width, pad_spacing_y))
            trans_left = pya.DTrans(-pad_spacing_x/2 - pad_connection_box_width, -pad_spacing_y/2)
            trans_right = pya.DTrans(pad_spacing_x/2, -pad_spacing_y/2)
            pads_region.insert((trans*trans_left*pad_connection_box).to_itype(self.layout.dbu))
            pads_region.insert((trans*trans_right*pad_connection_box).to_itype(self.layout.dbu))

        if refpoint_distance is None:
            self.refpoints["{}_sw".format(refpoint_prefix)] = pos_sw
            self.refpoints["{}_nw".format(refpoint_prefix)] = pos_nw
            self.refpoints["{}_ne".format(refpoint_prefix)] = pos_ne
            self.refpoints["{}_se".format(refpoint_prefix)] = pos_se
        else:
            self.refpoints["{}_sw".format(refpoint_prefix)] = pos_sw + pya.DVector(-pad_width/2 + refpoint_distance, 0)
            self.refpoints["{}_nw".format(refpoint_prefix)] = pos_nw + pya.DVector(-pad_width/2 + refpoint_distance, 0)
            self.refpoints["{}_ne".format(refpoint_prefix)] = pos_ne + pya.DVector(pad_width/2 - refpoint_distance, 0)
            self.refpoints["{}_se".format(refpoint_prefix)] = pos_se + pya.DVector(pad_width/2 - refpoint_distance, 0)

    def produce_etched_region(self, metal_region, pos, width, height):
        """Produces structures in metal gap layer.

        Subtracts metal_region from a region defined by width and height, and inserts resulting
        region to metal gap layer. Also adds grid avoidance for the area.

        Args:
            metal_region: region subtracted from the region in metal gap layer
            pos: center of the produced region (pya.DPoint)
            width: width of the produced region
            height: height of the produced region

        """
        test_area = pya.DPolygon([
            pya.DPoint(pos.x + width/2, pos.y + height/2),
            pya.DPoint(pos.x + width/2, pos.y - height/2),
            pya.DPoint(pos.x - width/2, pos.y - height/2),
            pya.DPoint(pos.x - width/2, pos.y + height/2),
        ])
        reg_test_area = pya.Region(test_area.to_itype(self.layout.dbu))
        # etched region
        reg_etch = reg_test_area - metal_region
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(reg_etch)
        # grid avoidance region
        reg_protect = reg_etch.extents(int(self.margin/self.layout.dbu))
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(reg_protect)
