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


from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.elements.element import Element
from kqcircuits.elements.f2f_connectors.flip_chip_connectors.flip_chip_connector_rf import FlipChipConnectorRf
from kqcircuits.elements.spiral_resonator_rectangle import SpiralResonatorRectangle
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_curved import WaveguideCoplanarCurved
from kqcircuits.elements.waveguide_coplanar_straight import WaveguideCoplanarStraight
from kqcircuits.util.geometry_helper import vector_length_and_direction

numerical_inaccuracy = 1e-7


class SpiralResonatorRectangleMultiface(SpiralResonatorRectangle):
    """The PCell declaration for a two-face rectangular spiral resonator.

    Otherwise similar to SpiralResonatorRectangle, but the resonator waveguide will change to face 1
    (through a flip-chip connector) after specified distance. WARNING: If the connector is located immediately next to
    corners, the connector is located in the next straight segment it can fit, so the distance is not exact. In this
    case, the other parameters should be adjusted to avoid having the connector right next to a corner.
    """

    connector_dist = Param(pdt.TypeDouble, "Distance of face to face connector from input", 0)

    def produce_impl(self):
        self.active_face_idx = 0  # used in add_segment() to control in which face the waveguide is created
        super().produce_impl()  # the add_segment() method overridden in this class is called in super().produce_impl()

    def add_segment(self, point1, point2, current_len, rotation, res_trans, space):
        """Inserts waveguides for a segment between point1 and point2.

        Same as base class add_segment(), but the segment can be created either in face 0 or face 1
        (or partly in both), depending on the current_len compared to self.connector_dist.

        Args:
            point1: start point of the segment
            point2: end point of the segment
            current_len: current length of the resonator waveguide
            rotation: rotation in units of 90-degrees, 0 for left-to-right segment, 1 for bottom-to-up segment,
                2 for right-to-left segment, 3 for up-to-bottom segment
            res_trans: transformation applied to the entire resonator
            space: space left for the next turn

        Returns:
            ``(current_len, final_segment, can_create_resonator)``

            Where ``current_len`` is length of the resonator waveguide after adding this segment.
            ``final_segment`` is True if this is the last segment of the resonator, False otherwise.
            ``can_create_resonator`` is True if it was possible to create the resonator with the
            given parameters, False otherwise.
        """
        if space + numerical_inaccuracy < 0.0:
            return current_len, False, False

        _, segment_dir, corner_offset, straight_len, curve_angle, final_segment = \
            self.get_segment_data(point1, point2, current_len, rotation, max(0.0, space))

        if (not final_segment and space < 2 * self.r) or \
                straight_len + numerical_inaccuracy < 0.0 or curve_angle - numerical_inaccuracy > 0.0:
            return current_len, False, False

        # add connector cell and get connector length
        connector_cell = self.add_element(FlipChipConnectorRf, Element)
        cell_refs = self.get_refpoints(connector_cell)
        connector_len, _ = vector_length_and_direction(cell_refs["b_port"] - cell_refs["t_port"])

        # straight waveguide part
        if straight_len > numerical_inaccuracy:
            # change face and create connector if at correct distance
            if self.active_face_idx == 0 and \
                    self.connector_dist + connector_len / 2 < current_len + straight_len + numerical_inaccuracy and \
                    connector_len < straight_len + numerical_inaccuracy:
                dist1 = max(connector_len / 2, self.connector_dist - current_len)
                connector_trans = pya.DTrans(rotation, False, point1 + (self.r + dist1) * segment_dir)
                _, connector_ref = self.insert_cell(connector_cell, res_trans * connector_trans)
                face_0_len = dist1 - connector_len / 2
                face_1_len = straight_len - dist1 - connector_len / 2
                if face_0_len > numerical_inaccuracy:
                    subcell = self.add_element(WaveguideCoplanarStraight, Element, l=face_0_len,
                                               face_ids=[self.face_ids[self.active_face_idx]])
                    trans = pya.DTrans(rotation, False, point1 + self.r * segment_dir)
                    self.insert_cell(subcell, res_trans*trans)
                self.active_face_idx = 1
                if face_1_len > numerical_inaccuracy:
                    subcell = self.add_element(WaveguideCoplanarStraight, Element, l=face_1_len,
                                               face_ids=[self.face_ids[self.active_face_idx]])
                    trans = pya.DTrans(rotation, False, res_trans.inverted()*connector_ref["t_port"])
                    self.insert_cell(subcell, res_trans*trans)
            else:
                subcell = self.add_element(WaveguideCoplanarStraight, Element, l=straight_len,
                                           face_ids=[self.face_ids[self.active_face_idx]])
                trans = pya.DTrans(rotation, False, point1 + self.r * segment_dir)
                self.insert_cell(subcell, res_trans*trans)

        # curved waveguide part
        if curve_angle < -numerical_inaccuracy:
            subcell = self.add_element(WaveguideCoplanarCurved, Element, alpha=curve_angle,
                                       face_ids=[self.face_ids[self.active_face_idx]])
            trans = res_trans*pya.DTrans(rotation + 1, False,
                                         point1 + (self.r + straight_len) * segment_dir + corner_offset)
            self.insert_cell(subcell, trans)
            if final_segment:
                WaveguideCoplanarCurved.produce_curve_termination(self, curve_angle, self.term2, trans,
                                                                  self.active_face_idx)
        elif final_segment:
            # in this case the straight segment was really the last segment, so need to terminate that
            WaveguideCoplanar.produce_end_termination(self, res_trans * point1,
                                                      res_trans * (point1 + (self.r + straight_len)*segment_dir),
                                                      self.term2, self.active_face_idx)

        if final_segment:
            if self.active_face_idx == 0:
                return current_len + straight_len - curve_angle * self.r, True, False
            self.active_face_idx = 0  # required because produce_spiral_resonator() may be called again

        return current_len + straight_len - curve_angle * self.r, final_segment, True
