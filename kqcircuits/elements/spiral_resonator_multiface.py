# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.element import Element
from kqcircuits.elements.flip_chip_connector.flip_chip_connector_rf import FlipChipConnectorRf
from kqcircuits.elements.spiral_resonator_auto import SpiralResonatorAuto
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_curved import WaveguideCoplanarCurved
from kqcircuits.elements.waveguide_coplanar_straight import WaveguideCoplanarStraight
from kqcircuits.util.geometry_helper import vector_length_and_direction
from kqcircuits.defaults import default_layers

numerical_inaccuracy = 1e-7


class SpiralResonatorMultiface(SpiralResonatorAuto):
    """The PCell declaration for a two-face rectangular spiral resonator.

    Otherwise similar to SpiralResonatorAuto, but the resonator waveguide will change to face 1
    (through a flip-chip connector) after specified distance. WARNING: If the connector is located
    immediately next to corners, there can be problems, like broken waveguides and the distance not
    being exact. In this case, the other parameters should be adjusted to avoid having the connector
    right next to a corner.
    """

    PARAMETERS_SCHEMA = {
        "connector_dist": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Distance of face to face connector from input",
            "default": 0
        },
    }

    def produce_impl(self):
        self.active_face_idx = 0  # used in add_segment() to control in which face the waveguide is created
        super().produce_impl()  # the add_segment() method overridden in this class is called in super().produce_impl()

    def add_segment(self, point1, point2, current_len, rotation, res_trans):
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

        Returns:
            ``(current_len, final_segment, can_create_resonator)``

            Where ``current_len`` is length of the resonator waveguide after adding this segment.
            ``final_segment`` is True if this is the last segment of the resonator, False otherwise.
            ``can_create_resonator`` is True if it was possible to create the resonator with the
            given parameters, False otherwise.
        """
        can_create_resonator = True
        created_connector = False

        segment_len, segment_dir, corner_offset, straight_len, curve_angle, final_segment = \
            self.get_segment_data(point1, point2, current_len, rotation, res_trans)

        if segment_len < 2*self.r + numerical_inaccuracy:
            can_create_resonator = False

        # straight waveguide part
        if straight_len > numerical_inaccuracy:

            # change face and create connector if at correct distance
            if self.active_face_idx == 0 and current_len + straight_len > self.connector_dist:
                # make sure the connector is not inside a corner (length of a connector is 60 um)
                dist1 = max(61, self.connector_dist - current_len)
                connector_trans = pya.DTrans(rotation, False, point1 + (self.r + dist1)*segment_dir)
                connector_cell = self.add_element(FlipChipConnectorRf, Element.PARAMETERS_SCHEMA)
                connector_inst, connector_ref = self.insert_cell(connector_cell, res_trans*connector_trans)
                face_0_len, _ = \
                    vector_length_and_direction(connector_ref["b_port"] - res_trans*(point1 + self.r*segment_dir))
                face_1_len, _ = \
                    vector_length_and_direction(connector_ref["t_port"] - res_trans*(point2 - self.r*segment_dir))
                face_1_len = min(face_1_len, straight_len - face_0_len)
                subcell = self.add_element(WaveguideCoplanarStraight, Element.PARAMETERS_SCHEMA,
                    l=face_0_len,
                    face_ids=[self.face_ids[self.active_face_idx]]
                )
                trans = pya.DTrans(rotation, False, point1 + self.r*segment_dir)
                self.insert_cell(subcell, res_trans*trans)
                self.active_face_idx = 1
                subcell = self.add_element(WaveguideCoplanarStraight, Element.PARAMETERS_SCHEMA,
                    l=face_1_len,
                    face_ids=[self.face_ids[self.active_face_idx]]
                )
                trans = pya.DTrans(rotation, False, res_trans.inverted()*connector_ref["t_port"])
                self.insert_cell(subcell, res_trans*trans)
                created_connector = True
            else:
                subcell = self.add_element(WaveguideCoplanarStraight, Element.PARAMETERS_SCHEMA,
                    l=straight_len,
                    face_ids=[self.face_ids[self.active_face_idx]]
                )
                trans = pya.DTrans(rotation, False, point1 + self.r*segment_dir)
                self.insert_cell(subcell, res_trans*trans)
        else:
            # (not sure if this can ever be reached, but might be possible due to numerical issues)
            # in this case the previous curve was really the last segment, so need to terminate that
            WaveguideCoplanar.produce_end_termination(self, res_trans*point1, res_trans*(point1 + self.r*segment_dir),
                                                      self.term2, self.active_face_idx)
            final_segment = True
        # curved waveguide part
        if curve_angle < -numerical_inaccuracy:
            subcell = self.add_element(WaveguideCoplanarCurved, Element.PARAMETERS_SCHEMA,
                alpha=curve_angle,
                face_ids=[self.face_ids[self.active_face_idx]]
            )
            trans = res_trans*pya.DTrans(rotation + 1, False, point2 - self.r*segment_dir + corner_offset)
            self.insert_cell(subcell, trans)
            if final_segment:
                WaveguideCoplanarCurved.produce_curve_termination(self, curve_angle, self.term2, trans,
                                                                  self.active_face_idx)
        else:
            # in this case the straight segment was really the last segment, so need to terminate that
            if created_connector:
                term_end_point = connector_ref["t_port"] + face_1_len*segment_dir
            else:
                term_end_point = point1 + (self.r + straight_len)*segment_dir
            WaveguideCoplanar.produce_end_termination(self, res_trans*point1, res_trans*term_end_point, self.term2,
                                                      self.active_face_idx)
            final_segment = True

        current_len = WaveguideCoplanar.get_length(self.cell, self.get_layer("annotations"))
        if final_segment:
            self.active_face_idx = 0  # required because produce_spiral_resonator() may be called again

        return current_len, final_segment, can_create_resonator
