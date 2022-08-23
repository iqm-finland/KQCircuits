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


from kqcircuits.chips.chip import Chip
from kqcircuits.elements.spiral_resonator_polygon import SpiralResonatorPolygon, rectangular_parameters
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter, t_cross_parameters
from kqcircuits.pya_resolver import pya
from kqcircuits.util.coupler_lib import cap_params
from kqcircuits.util.geometry_helper import point_shift_along_vector
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.chips.quality_factor import QualityFactor


@add_parameters_from(QualityFactor, "res_lengths", "n_fingers", "l_fingers", "type_coupler",
                     res_a=[10, 10, 10, 20, 10, 5], res_b=[6, 6, 6, 12, 6, 3])
@add_parameters_from(Chip, frames_enabled=[0, 1])
@add_parameters_from(SpiralResonatorPolygon, "bridge_spacing")
class QualityFactorTwoface(Chip):
    """The PCell declaration for a QualityFactorTwoFace chip.

     Preliminary class for flip-chip resonators.
     """

    resonator_types = Param(pdt.TypeList, "Resonator types (capped, twoface, etched, or solid)", ["capped"] * 6,
                            docstring="Choices: 'capped', 'twoface', 'etched', 'solid'")
    resonator_faces = Param(pdt.TypeList, "Resonator face order list", [0, 1])
    connector_distances = Param(pdt.TypeList, "Resonator input to face to face connector",
                                [500, 1300, 2100, 2900, 3700, 4500], unit="[μm]",
                                docstring="Distances of face to face connectors from resonator inputs")
    spiral_box_height = Param(pdt.TypeDouble, "Spiral resonator box height", 2000)
    spiral_box_width = Param(pdt.TypeDouble, "Spiral resonator box width", 500)
    x_indentation = Param(pdt.TypeDouble, "Resonator/connector indentation from side edges", 800)
    cap_res_distance = Param(pdt.TypeDouble, "Distance between spiral resonator and capacitor", 200)
    waveguide_indentation = Param(pdt.TypeDouble, "Waveguide indentation from top chip edge", 500)
    extra_resonator_avoidance = Param(pdt.TypeList, "Added avoidance", [0, 0, 0, 0, 0, 0], unit="[μm]",
                                      docstring="Added avoidance around resonators [μm]")

    def build(self):
        self._produce_resonators()

    def _produce_resonators(self):
        # Interpretation of parameter lists
        res_lengths = [float(foo) for foo in self.res_lengths]
        res_a = [float(foo) for foo in self.res_a]
        res_b = [float(foo) for foo in self.res_b]
        n_fingers = [float(foo) for foo in self.n_fingers]
        type_coupler = self.type_coupler
        l_fingers = [float(foo) for foo in self.l_fingers]
        connector_distances = [float(foo) for foo in self.connector_distances]
        face1_box = self.get_box(1)
        extra_resonator_avoidance = [float(i) for i in self.extra_resonator_avoidance]

        # Constants
        left_x = face1_box.p1.x + self.waveguide_indentation
        right_x = face1_box.p2.x - self.waveguide_indentation
        left_connector = face1_box.p1.x + self.x_indentation
        right_connector = face1_box.p2.x - self.x_indentation
        mid_y = (face1_box.p1.y + face1_box.p2.y) / 2
        face_config = [self.face_ids[int(i)] for i in self.resonator_faces]

        # Create resonators
        resonators = len(self.res_lengths)
        tl_start = pya.DPoint(left_connector + self.spiral_box_width, mid_y)
        v_res_step = pya.DPoint(right_connector - left_connector - self.spiral_box_width, 0) * \
                     (1. / resonators)
        cell_cross = self.add_element(WaveguideCoplanarSplitter, **t_cross_parameters(
            length_extra_side=5 * self.a_capped, a=self.a_capped, b=self.b_capped, a2=self.a_capped, b2=self.b_capped,
            face_ids=face_config))

        for i in range(resonators):
            # Determine opposite face protection for capacitors and resonators
            res_protect_opposite_face = self.protect_opposite_face
            if self.resonator_types[i] in ["etched", "capped"]:
                res_protect_opposite_face = False
            elif self.resonator_types[i] == "solid":
                res_protect_opposite_face = True

            # Create capacitor
            cplr_params = cap_params(
                n_fingers[i], l_fingers[i], type_coupler[i], protect_opposite_face=res_protect_opposite_face,
                face_ids=face_config, a=res_a[i], b=res_b[i], a2=self.a_capped, b2=self.b_capped)
            cplr = self.add_element(**cplr_params)
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
            inst_cplr, _ = self.insert_cell(cplr, cplr_trans)
            self.refpoints[f'res_{i}_coupler'] = cplr_pos

            # Y-indentation for spiral resonator
            endpoint = point_shift_along_vector(cplr_refpoints_rel["port_b"],
                                                cplr_refpoints_rel["port_b_corner"],
                                                self.cap_res_distance)

            inst_cpw, _ = self.insert_cell(WaveguideCoplanar, **{**self.cell.pcell_parameters_by_name(), **{
                "path": pya.DPath([cplr_refpoints_rel["port_b"], endpoint], 1),
                "term2": 0,
                "a": res_a[i],
                "b": res_b[i],
                "r": self.r,
                "protect_opposite_face": res_protect_opposite_face,
                "face_ids": face_config,
                "margin": self.margin}},
                                           trans=pya.DTrans(cplr_pos) * rotation)

            pos_res_start = cplr_pos - rot_3 * endpoint

            # Spiral resonator
            if self.resonator_types[i] == "twoface":
                res_params = {'connector_dist': connector_distances[i] - self.cap_res_distance, "bridge_spacing": 0}
            elif self.resonator_types[i] == "etched":
                res_params = {
                    'name': 'resonator{}'.format(i),
                    "airbridge_type": "Airbridge Multi Face",
                    "include_bumps": False,
                    "bridge_length": res_a[i] + 2 * (res_b[i] + self.margin),
                    "bridge_width": 2,
                    "pad_length": 2,
                    "bridge_spacing": self.bridge_spacing,
                }
            else:
                res_params = {'name': 'resonator{}'.format(i), "bridge_spacing": 0}
            inst_res, _ = self.insert_cell(SpiralResonatorPolygon,
                                           margin=self.margin + extra_resonator_avoidance[i],
                                           **rectangular_parameters(
                                               right_space=self.spiral_box_height - self.cap_res_distance,
                                               above_space=0,
                                               below_space=self.spiral_box_width,
                                               length=res_lengths[i] - self.cap_res_distance,
                                               a=res_a[i],
                                               b=res_b[i],
                                               face_ids=face_config,
                                               protect_opposite_face=res_protect_opposite_face,
                                               **res_params),
                                           trans=pya.DTrans(pos_res_start) * rotation)

            # Top chip etching and grid avoidance above resonator
            if self.resonator_types[i] == "etched":
                l0 = self.get_layer("ground_grid_avoidance", int(self.resonator_faces[0]))
                region = pya.Region(inst_res.cell.begin_shapes_rec(l0)).transformed(inst_res.trans)
                region += pya.Region(inst_cpw.cell.begin_shapes_rec(l0)).transformed(inst_cpw.trans)
                region += pya.Region(inst_cplr.cell.begin_shapes_rec(l0)).transformed(inst_cplr.trans)
                opposite_face = int(self.resonator_faces[1])
                self.cell.shapes(self.get_layer("ground_grid_avoidance", opposite_face)).insert(region)
                self.cell.shapes(self.get_layer("base_metal_gap_wo_grid", opposite_face)).insert(region)

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
        self.produce_launchers("SMA8", launcher_assignments={8: "PL-IN", 3: "PL-OUT"})

        # Waveguides to the launchers
        if self.waveguide_indentation > 0.0:
            nodes_left = [Node(self.refpoints["PL-IN_port"]),
                          Node((face1_box.p1.x, self.refpoints["PL-IN_port"].y), a=self.a_capped, b=self.b_capped),
                          Node((left_x, self.refpoints["PL-IN_port"].y)),
                          Node((left_x, mid_y)),
                          Node((left_connector, mid_y), face_id=face_config[0]),
                          Node(left_point)]
            nodes_right = [Node(self.refpoints["PL-OUT_port"]),
                           Node((face1_box.p2.x, self.refpoints["PL-OUT_port"].y), a=self.a_capped, b=self.b_capped),
                           Node((right_x, self.refpoints["PL-OUT_port"].y)),
                           Node((right_x, mid_y)),
                           Node((right_connector, mid_y), face_id=face_config[0]),
                           Node(right_point)]
        else:
            nodes_left = [Node(self.refpoints["PL-IN_port"]),
                          Node((left_x, self.refpoints["PL-IN_port"].y)),
                          Node((left_x, mid_y)),
                          Node((face1_box.p1.x, mid_y), a=self.a_capped, b=self.b_capped),
                          Node((left_connector, mid_y), face_id=face_config[0]),
                          Node(left_point)]
            nodes_right = [Node(self.refpoints["PL-OUT_port"]),
                           Node((right_x, self.refpoints["PL-OUT_port"].y)),
                           Node((right_x, mid_y)),
                           Node((face1_box.p2.x, mid_y), a=self.a_capped, b=self.b_capped),
                           Node((right_connector, mid_y), face_id=face_config[0]),
                           Node(right_point)]
        self.insert_cell(WaveguideComposite, nodes=nodes_left)
        self.insert_cell(WaveguideComposite, nodes=nodes_right)
