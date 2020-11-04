# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import sys
from importlib import reload

from kqcircuits.pya_resolver import pya

from kqcircuits.chips.multi_face.multi_face import MultiFace
from kqcircuits.elements.spiral_resonator_multiface import SpiralResonatorMultiface

from kqcircuits.elements.waveguide_coplanar_bridged import WaveguideCoplanarBridged, Node, NodeType
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_tcross import WaveguideCoplanarTCross
from kqcircuits.util.coupler_lib import produce_library_capacitor
from kqcircuits.elements.spiral_resonator_auto import SpiralResonatorAuto
from kqcircuits.util.geometry_helper import point_shift_along_vector

reload(sys.modules[MultiFace.__module__])
version = 1


class QualityFactorTwoface(MultiFace):
    """The PCell declaration for an QualityFactorTwoFace MultiFace chip.

     Preliminary class for flip-chip resonators.
     """

    PARAMETERS_SCHEMA = {
        "res_lengths": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Resonator lengths [μm]",
            "docstring": "Physical length of resonators [μm]",
            "default": [5434, 5429, 5374, 5412, 5493, 5589]
        },
        "n_fingers": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Number of fingers of the coupler",
            "docstring": "Fingers in planar capacitors",
            "default": [4, 4, 2, 4, 4, 4]
        },
        "l_fingers": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Length of fingers [μm]",
            "docstring": "Length of the capacitor fingers [μm]",
            "default": [23.1, 9.9, 14.1, 10, 21, 28, 3]
        },
        "type_coupler": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Coupler type",
            "default": ["square", "square", "square", "plate", "plate", "plate"]
        },
        "res_a": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Resonator waveguide center conductor width [μm]",
            "docstring": "Width of the center conductor in the resonator [μm]",
            "default": 10
        },
        "res_b": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Resonator waveguide gap width [μm]",
            "docstring": "Width of the gap in the resonator [μm]",
            "default": 10
        },
        "resonator_type": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Routing type",
            "default": "capped",
            "choices": [["Capped (1)", "capped"],
                        ["Two-face resonator (2)", "twoface"],
                        ["Resonator on top (3)", "top"]]
        },
        "connector_distances": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Resonator input to face to face connector [μm]",
            "docstring": "Distances of face to face connectors from resonator inputs",
            "default": [500, 1300, 2100, 2900, 3700, 4500]
        },
        "spiral_box_height": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Spiral resonator box height",
            "default": 2000
        },
        "spiral_box_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Spiral resonator box width",
            "default": 500
        }
    }

    def produce_impl(self):
        self._produce_resonators()

        # Basis chip with possibly ground plane grid
        super().produce_impl()

    def _produce_resonators(self):
        # Magic parameters

        cap_indentation = 200  # indentation counted from finger capacitor,
        # so the spiral resonator distance from TL is controllable
        tl_connector_indent = 525

        face_config = ["t", "b"] if self.resonator_type == "top" else ["b", "t"]

        # Interpretation of parameter lists
        res_lengths = [float(foo) for foo in self.res_lengths]
        n_fingers = [int(foo) for foo in self.n_fingers]
        type_coupler = self.type_coupler
        l_fingers = [float(foo) for foo in self.l_fingers]
        connector_distances = [float(foo) for foo in self.connector_distances]

        # Launchers
        launchers = self.produce_launchers_SMA8(enabled=["WN", "EN"])

        # Taper locations
        taper_pos_left = pya.DPoint(self.face1_box.p1.x,
                                    self.refpoints["WN_port"].y)  # add taper to produce impedance match
        taper_pos_right = pya.DPoint(self.face1_box.p2.x - 100,
                                     self.refpoints["EN_port"].y)  # add taper to produce impedance match

        marker_safety = 1.5e3  # depends on the marker size

        if self.resonator_type == "top":
            connector_node = Node(NodeType.FC_BUMP, pya.DPoint(2000 + tl_connector_indent, 5000))
        else:
            connector_node = Node(NodeType.WAVEGUIDE, pya.DPoint(2000 + tl_connector_indent, 5000))

        final_point = pya.DPoint(2000 + tl_connector_indent + 100, 5000)
        nodes = [Node(NodeType.WAVEGUIDE, self.refpoints["WN_port"], a=self.a, b=self.b),
                 Node(NodeType.WAVEGUIDE, taper_pos_left, a=self.a_capped, b=self.b_capped),
                 Node(NodeType.WAVEGUIDE, pya.DPoint(2000, self.refpoints["WN_port"].y)),
                 Node(NodeType.WAVEGUIDE, pya.DPoint(2000, 5000)),
                 connector_node,
                 Node(NodeType.WAVEGUIDE, final_point)
                 ]

        self.insert_cell(WaveguideCoplanarBridged,
                         nodes=nodes,
                         margin=self.margin,
                         a=self.a_capped,
                         b=self.b_capped
                         )

        points_fl = [final_point]
        tl_start = points_fl[-1]

        resonators = len(self.res_lengths)
        v_res_step = (pya.DPoint(self.refpoints["EN_port"].x, 5000) -
                      pya.DPoint(self.refpoints["WN_port"].x, 5000) -
                      pya.DVector((self.r * 4 + marker_safety * 2), 0)
                      ) * (1. / resonators)
        cell_cross = self.add_element(WaveguideCoplanarTCross,
                                   length_extra_side=5 * self.a, a=self.a_capped, b=self.b_capped, a2=self.a_capped,
                                   b2=self.b_capped,
                                   face_ids=face_config)

        for i in range(resonators):
            cplr = produce_library_capacitor(self.layout, n_fingers[i], l_fingers[i], type_coupler[i],
                                             face_ids=face_config)
            cplr_refpoints_rel = self.get_refpoints(cplr)

            # rotate if bool(i%2)
            if bool(i % 2):
                rotation = pya.DTrans.R90 * pya.DTrans.M0
                rot_2 = pya.DTrans.M0
                rot_3 = pya.DTrans.R270
                cplr_pos_post = pya.DTrans.R90 * rot_2 * cplr_refpoints_rel["port_b"]

            else:
                rotation = pya.DTrans.R270
                rot_2 = pya.DTrans.R0
                rot_3 = pya.DTrans.R90
                cplr_pos_post = pya.DTrans.R90 * rot_2 * cplr_refpoints_rel["port_b"] * -1

            # Cross
            cross_trans = pya.DTrans(tl_start + v_res_step * (i + 0.5)) * rot_2
            inst_cross, cross_refpoints_abs = self.insert_cell(cell_cross, cross_trans)

            # Coupler
            cplr_pos = cross_refpoints_abs["port_bottom"] + cplr_pos_post
            cplr_trans = pya.DTrans(1, False, cplr_pos.x, cplr_pos.y)
            self.insert_cell(cplr, cplr_trans)

            # indentation for spiral resonator
            endpoint = point_shift_along_vector(cplr_refpoints_rel["port_b"],
                                                cplr_refpoints_rel["port_b_corner"],
                                                cap_indentation)

            self.insert_cell(WaveguideCoplanar, **{**self.cell.pcell_parameters_by_name(), **{
                "path": pya.DPath(
                    [cplr_refpoints_rel["port_b"],
                     endpoint], 1),
                "term2": 0,
                "a": self.a_capped,
                "b": self.b_capped,
                "face_ids": face_config,
                "margin": self.margin}},
                trans=pya.DTrans(cplr_pos) * rotation)

            pos_res_start = cplr_pos - rot_3 * endpoint

            if self.resonator_type == "twoface":
                cell_res_even_width = self.add_element(SpiralResonatorMultiface,
                                                    right_space=self.spiral_box_height - cap_indentation,
                                                    above_space=0,
                                                    below_space=self.spiral_box_width,
                                                    length=res_lengths[i] - cap_indentation,
                                                    a=self.res_a,
                                                    b=self.res_b,
                                                    margin=self.margin,
                                                    connector_dist=connector_distances[i] - cap_indentation,
                                                    face_ids=face_config
                                                    )

            else:
                cell_res_even_width = self.add_element(SpiralResonatorAuto,
                                                    right_space=self.spiral_box_height - cap_indentation,
                                                    above_space=0,
                                                    below_space=self.spiral_box_width,
                                                    length=res_lengths[i] - cap_indentation,
                                                    a=self.res_a,
                                                    b=self.res_b,
                                                    margin=self.margin,
                                                    face_ids=face_config
                                                    )

            self.insert_cell(cell_res_even_width, pya.DTrans(pos_res_start) * rotation)
            # Feedline
            self.insert_cell(WaveguideCoplanar, **{**self.cell.pcell_parameters_by_name(), **{
                "path": pya.DPath(points_fl + [
                    cross_refpoints_abs["port_left"]
                ], 1),
                "term2": 0,
                "a": self.a_capped,
                "b": self.b_capped,
                "margin": self.margin,
                "face_ids": face_config
            }})
            points_fl = [cross_refpoints_abs["port_right"]]

        if self.resonator_type == "top":
            connector_node = Node(NodeType.FC_BUMP, pya.DPoint(8000 - tl_connector_indent + 103 , 5000))
        else:
            connector_node = Node(NodeType.WAVEGUIDE, pya.DPoint(8000 - tl_connector_indent + 50, 5000))

        # Last feedline
        nodes = [Node(NodeType.WAVEGUIDE, points_fl[-1], a=self.a_capped, b=self.b_capped),
                 connector_node,
                 Node(NodeType.WAVEGUIDE, pya.DPoint(8000, 5000)),
                 Node(NodeType.WAVEGUIDE, pya.DPoint(8000, self.refpoints["EN_port"].y)),
                 Node(NodeType.WAVEGUIDE, taper_pos_right, a=self.a, b=self.b),
                 Node(NodeType.WAVEGUIDE, self.refpoints["EN_port"])
                 ]

        self.insert_cell(WaveguideCoplanarBridged, nodes=nodes, margin=self.margin, a=self.a, b=self.b,
                         face_ids=face_config)
