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


from kqcircuits.chips.multi_face.multi_face import MultiFace
from kqcircuits.elements.spiral_resonator_rectangle import SpiralResonatorRectangle
from kqcircuits.elements.spiral_resonator_rectangle_multiface import SpiralResonatorRectangleMultiface
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_tcross import WaveguideCoplanarTCross
from kqcircuits.pya_resolver import pya
from kqcircuits.util.coupler_lib import produce_library_capacitor
from kqcircuits.util.geometry_helper import point_shift_along_vector
from kqcircuits.util.parameters import Param, pdt

version = 1


class QualityFactorTwoface(MultiFace):
    """The PCell declaration for an QualityFactorTwoFace MultiFace chip.

     Preliminary class for flip-chip resonators.
     """

    res_lengths = Param(pdt.TypeList, "Resonator lengths", [5434, 5429, 5374, 5412, 5493, 5589], unit="[μm]",
                        docstring="Physical length of resonators [μm]")
    n_fingers = Param(pdt.TypeList, "Number of fingers of the coupler", [4, 4, 2, 4, 4, 4],
                      docstring="Fingers in planar capacitors")
    l_fingers = Param(pdt.TypeList, "Length of fingers", [23.1, 9.9, 14.1, 10, 21, 28], unit="[μm]",
                      docstring="Length of the capacitor fingers [μm]")
    type_coupler = Param(pdt.TypeList, "Coupler type",
                         ["interdigital", "interdigital", "interdigital", "gap", "gap", "gap"])
    res_a = Param(pdt.TypeList, "Resonator waveguide center conductor width", [10, 10, 10, 20, 10, 5], unit="[μm]",
                  docstring="Width of the center conductor in the resonators [μm]")
    res_b = Param(pdt.TypeList, "Resonator waveguide gap width", [6, 6, 6, 12, 6, 3], unit="[μm]",
                  docstring="Width of the gap in the resonators [μm]")
    resonator_type = Param(pdt.TypeString, "Routing type", "capped",
                           choices=[["Capped (1)", "capped"], ["Two-face resonator (2)", "twoface"],
                                    ["Resonator on top (3)", "top"], ["Etched top chip (4)", "etched"],
                                    ["Solid top chip (5)", "solid"]])
    connector_distances = Param(pdt.TypeList, "Resonator input to face to face connector",
                                [500, 1300, 2100, 2900, 3700, 4500], unit="[μm]",
                                docstring="Distances of face to face connectors from resonator inputs")
    spiral_box_height = Param(pdt.TypeDouble, "Spiral resonator box height", 2000)
    spiral_box_width = Param(pdt.TypeDouble, "Spiral resonator box width", 500)
    x_indentation = Param(pdt.TypeDouble, "Resonator/connector indentation from side edges", 800)
    cap_res_distance = Param(pdt.TypeDouble, "Distance between spiral resonator and capacitor", 200)
    waveguide_indentation = Param(pdt.TypeDouble, "Waveguide indentation from top chip edge", 500)

    def produce_impl(self):
        self._produce_resonators()

        # Basis chip with possibly ground plane grid
        super().produce_impl()

    def _produce_resonators(self):
        # Interpretation of parameter lists
        res_lengths = [float(foo) for foo in self.res_lengths]
        res_a = [float(foo) for foo in self.res_a]
        res_b = [float(foo) for foo in self.res_b]
        n_fingers = [int(foo) for foo in self.n_fingers]
        type_coupler = self.type_coupler
        l_fingers = [float(foo) for foo in self.l_fingers]
        connector_distances = [float(foo) for foo in self.connector_distances]

        # Constants
        left_x = self.face1_box.p1.x + self.waveguide_indentation
        right_x = self.face1_box.p2.x - self.waveguide_indentation
        left_connector = self.face1_box.p1.x + self.x_indentation
        right_connector = self.face1_box.p2.x - self.x_indentation
        mid_y = (self.face1_box.p1.y + self.face1_box.p2.y) / 2
        face_config = ["t", "b"] if self.resonator_type == "top" else ["b", "t"]

        # Create resonators
        resonators = len(self.res_lengths)
        tl_start = pya.DPoint(left_connector + self.spiral_box_width, mid_y)
        v_res_step = pya.DPoint(right_connector - left_connector - self.spiral_box_width, 0) * \
                     (1. / resonators)
        cell_cross = self.add_element(WaveguideCoplanarTCross, length_extra_side=5 * self.a_capped,
                                      a=self.a_capped, b=self.b_capped, a2=self.a_capped, b2=self.b_capped,
                                      face_ids=face_config, margin=self.margin)

        for i in range(resonators):
            cplr = produce_library_capacitor(self.layout, n_fingers[i], l_fingers[i], type_coupler[i],
                                             face_ids=face_config, margin=self.margin,
                                             a=res_a[i], b=res_b[i], a2=self.a_capped, b2=self.b_capped)
            cplr_refpoints_rel = self.get_refpoints(cplr)

            # Every second resonator is on the same side. Define transformations here:
            if i % 2:
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
            _, cross_refpoints_abs = self.insert_cell(cell_cross, cross_trans)

            # Coupler
            cplr_pos = cross_refpoints_abs["port_bottom"] + cplr_pos_post
            cplr_trans = pya.DTrans(cplr_pos.x, cplr_pos.y) * rot_3
            self.insert_cell(cplr, cplr_trans)

            # Y-indentation for spiral resonator
            endpoint = point_shift_along_vector(cplr_refpoints_rel["port_b"],
                                                cplr_refpoints_rel["port_b_corner"],
                                                self.cap_res_distance)

            self.insert_cell(WaveguideCoplanar, **{**self.cell.pcell_parameters_by_name(), **{
                "path": pya.DPath([cplr_refpoints_rel["port_b"], endpoint], 1),
                "term2": 0,
                "a": res_a[i],
                "b": res_b[i],
                "r": self.r,
                "face_ids": face_config,
                "margin": self.margin}},
                             trans=pya.DTrans(cplr_pos) * rotation)

            pos_res_start = cplr_pos - rot_3 * endpoint

            # Spiral resonator
            if self.resonator_type == "twoface":
                cell_res_even_width = self.add_element(SpiralResonatorRectangleMultiface,
                                                       right_space=self.spiral_box_height - self.cap_res_distance,
                                                       above_space=0,
                                                       below_space=self.spiral_box_width,
                                                       length=res_lengths[i] - self.cap_res_distance,
                                                       a=res_a[i],
                                                       b=res_b[i],
                                                       margin=self.margin,
                                                       connector_dist=connector_distances[i] - self.cap_res_distance,
                                                       face_ids=face_config,
                                                       r=self.r
                                                       )
            else:
                cell_res_even_width = self.add_element(SpiralResonatorRectangle,
                                                       name='resonator{}'.format(i),
                                                       right_space=self.spiral_box_height - self.cap_res_distance,
                                                       above_space=0,
                                                       below_space=self.spiral_box_width,
                                                       length=res_lengths[i] - self.cap_res_distance,
                                                       a=res_a[i],
                                                       b=res_b[i],
                                                       margin=self.margin,
                                                       face_ids=face_config,
                                                       r=self.r
                                                       )
            self.insert_cell(cell_res_even_width, pya.DTrans(pos_res_start) * rotation)

            # Feedline
            if i == 0:
                left_point = cross_refpoints_abs["port_left"]
            else:
                self.insert_cell(WaveguideCoplanar, **{**self.cell.pcell_parameters_by_name(), **{
                    "path": pya.DPath([right_point] + [cross_refpoints_abs["port_left"]], 1),
                    "term2": 0,
                    "a": self.a_capped,
                    "b": self.b_capped,
                    "r": self.r,
                    "margin": self.margin,
                    "face_ids": face_config
                }})
            right_point = cross_refpoints_abs["port_right"]

        # Launchers
        self.produce_launchers_SMA8(enabled=["WN", "EN"])

        # Waveguides to the launchers
        if self.waveguide_indentation > 0.0:
            nodes_left = [Node(self.refpoints["WN_port"]),
                          Node((self.face1_box.p1.x, self.refpoints["WN_port"].y), a=self.a_capped, b=self.b_capped),
                          Node((left_x, self.refpoints["WN_port"].y)),
                          Node((left_x, mid_y)),
                          Node((left_connector, mid_y), face_id=face_config[0]),
                          Node(left_point)]
            nodes_right = [Node(self.refpoints["EN_port"]),
                           Node((self.face1_box.p2.x, self.refpoints["EN_port"].y), a=self.a_capped, b=self.b_capped),
                           Node((right_x, self.refpoints["EN_port"].y)),
                           Node((right_x, mid_y)),
                           Node((right_connector, mid_y), face_id=face_config[0]),
                           Node(right_point)]
        else:
            nodes_left = [Node(self.refpoints["WN_port"]),
                          Node((left_x, self.refpoints["WN_port"].y)),
                          Node((left_x, mid_y)),
                          Node((self.face1_box.p1.x, mid_y), a=self.a_capped, b=self.b_capped),
                          Node((left_connector, mid_y), face_id=face_config[0]),
                          Node(left_point)]
            nodes_right = [Node(self.refpoints["EN_port"]),
                           Node((right_x, self.refpoints["EN_port"].y)),
                           Node((right_x, mid_y)),
                           Node((self.face1_box.p2.x, mid_y), a=self.a_capped, b=self.b_capped),
                           Node((right_connector, mid_y), face_id=face_config[0]),
                           Node(right_point)]
        self.insert_cell(WaveguideComposite, nodes=nodes_left, margin=self.margin, a=self.a, b=self.b)
        self.insert_cell(WaveguideComposite, nodes=nodes_right, margin=self.margin, a=self.a, b=self.b)

        # Top chip etching and ground grid avoidance
        if self.resonator_type == "etched" or self.resonator_type == "solid":
            region = pya.Region(self.cell.begin_shapes_rec(self.get_layer("ground_grid_avoidance", face_id=0)))
            region &= pya.Region([pya.DPolygon([
                self.face1_box.p1, pya.DPoint(self.face1_box.p1.x, self.face1_box.p2.y),
                self.face1_box.p2, pya.DPoint(self.face1_box.p2.x, self.face1_box.p1.y)
            ]).to_itype(self.layout.dbu)])
            if self.resonator_type == "etched":
                self.cell.shapes(self.get_layer("base_metal_gap_wo_grid", face_id=1)).insert(region)
            self.cell.shapes(self.get_layer("ground_grid_avoidance", face_id=1)).insert(region)
