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
from math import ceil

from kqcircuits.chips.chip import Chip
from kqcircuits.elements.spiral_resonator_polygon import SpiralResonatorPolygon
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node
from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter
from kqcircuits.pya_resolver import pya
from kqcircuits.util.coupler_lib import cap_params
from kqcircuits.util.geometry_helper import get_angle
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
                                [500, 1300, 2100, 2900, 3700, 4500] * 2, unit="[μm]",
                                docstring="Distances of face to face connectors from resonator inputs")
    spiral_box_height = Param(pdt.TypeDouble, "Spiral resonator box height", 2000)
    spiral_box_width = Param(pdt.TypeDouble, "Spiral resonator box width", 500)
    x_indentation = Param(pdt.TypeDouble, "Resonator/connector indentation from side edges", 800)
    cap_res_distance = Param(pdt.TypeDouble, "Distance between spiral resonator and capacitor", 200)
    waveguide_indentation = Param(pdt.TypeDouble, "Waveguide indentation from top chip edge", 500)
    extra_resonator_avoidance = Param(pdt.TypeList, "Added avoidance", [0, 0, 0, 0, 0, 0], unit="[μm]",
                                      docstring="Added avoidance around resonators [μm]")
    etch_opposite_face_margin = Param(pdt.TypeDouble, "Margin around the waveguide to etch on the opposite face " +
                                                      "for 'etched' type resonators", 5)

    def build(self):
        self._produce_resonators()

    def _produce_resonators(self):
        self.produce_launchers("SMA8", launcher_assignments={
            3: "PL-1-OUT",
            8: "PL-1-IN",
        })

        # Constants
        face1_box = self.get_box(1)
        left_x = face1_box.left + self.waveguide_indentation
        right_x = face1_box.right - self.waveguide_indentation
        left_connector = face1_box.left + self.x_indentation
        right_connector = face1_box.right - self.x_indentation
        mid_y = face1_box.center().y
        resonator_face_ids = [self.face_ids[int(i)] for i in self.resonator_faces]

        n_resonators = len(self.res_lengths)
        start_x = left_connector + self.spiral_box_width
        resonator_spacing = (right_connector - left_connector - self.spiral_box_width) / n_resonators
        resonator_positions = [pya.DPoint(start_x + (i + 0.5) * resonator_spacing, mid_y) for i in range(n_resonators)]
        resonator_directions = [90, 270] * ceil(n_resonators / 2)

        # Create probeline
        tee_length = self.a_capped / 2 + self.b_capped
        side_tee_length = tee_length + 5 * self.a_capped
        splitter_nodes = [Node(point, WaveguideCoplanarSplitter, angles=[0, 180, angle],
                               lengths=[tee_length, tee_length, side_tee_length], inst_name=f"{i}_t")
                          for i, (point, angle) in enumerate(zip(resonator_positions, resonator_directions))]

        probeline = self.add_element(
            WaveguideComposite,
            nodes=[
                Node(self.refpoints["PL-1-IN_port"]),
                Node(pya.DPoint(face1_box.left, self.refpoints["PL-1-IN_port"].y), a=self.a_capped, b=self.b_capped,
                     taper_length=100),
                Node(pya.DPoint(left_x, self.refpoints["PL-1-IN_port"].y)),
                Node(pya.DPoint(left_x, mid_y)),
                Node(pya.DPoint(left_connector, mid_y), face_id=resonator_face_ids[0]),
                *splitter_nodes,
                Node(pya.DPoint(right_connector, mid_y), face_id=self.face_ids[0]),
                Node(pya.DPoint(right_x, mid_y)),
                Node(pya.DPoint(right_x, self.refpoints["PL-1-OUT_port"].y)),
                Node(pya.DPoint(face1_box.right - 100, self.refpoints["PL-1-OUT_port"].y), a=self.a, b=self.b,
                     taper_length=100),
                Node(self.refpoints["PL-1-OUT_port"])
            ],
        )
        self.insert_cell(probeline, inst_name="pl")

        # Create resonators
        for i in range(n_resonators):
            self.produce_resonator(i, float(self.res_a[i]), float(self.res_b[i]), float(self.res_lengths[i]),
                                   float(self.n_fingers[i]), float(self.l_fingers[i]), self.type_coupler[i],
                                   resonator_face_ids, self.resonator_types[i], float(self.connector_distances[i]),
                                   float(self.extra_resonator_avoidance[i]), mirror=(i % 2 == 1))

    def produce_resonator(self, i, a, b, length, n_fingers, l_fingers, type_coupler, face_ids,
                          resonator_type="capped", connector_distance=0.0,
                          extra_resonator_avoidance=0.0, mirror=False):
        """
        Produce a single spiral resonator and corresponding input capacitor.

        The resonator is attached to the chip refpoint ``pl_{i}_t_port_c``, where `i` is the resonator index (this can
        be any identifier, as long as it is used the same way in the refpoint name). The direction of the resonator
        is set by the corresponding ``_corner`` refpoint, but the spiral can be left or right depending on ``mirror``.

        Args:
            i: Resonator index
            a: CPW line width
            b: CPW gap width
            length: Resonator length (excluding capacitor)
            n_fingers: Capacitor finger number, or finger_control for ``SmoothCapacitor``
            l_fingers: Capacitor finger length
            type_coupler: Type of capacitor, see ``cap_params``
            face_ids: list of face ids for the resonator
            resonator_type: String, type of resonator, one of ``etched``, ``capped``, ``solid`` or ``twoface``
            connector_distance: For ``twoface`` resonators, distance of the flip chip connector starting from capacitor
            extra_resonator_avoidance: Extra ``ground_grid_avoidance`` margin around the resonator
            mirror: Turn clockwise if False, or counter-clockwise if True.
        """

        if resonator_type in ["etched", "capped"]:
            protect_opposite_face = False
        elif resonator_type == "solid":
            protect_opposite_face = True
        else:
            protect_opposite_face = self.protect_opposite_face

        # Get starting angle
        start = self.refpoints[f"pl_{i}_t_port_c"]
        start_corner = self.refpoints[f"pl_{i}_t_port_c_corner"]
        start_angle = get_angle(start_corner - start)

        # Capacitor
        cplr_params = cap_params(
            n_fingers, l_fingers, type_coupler, protect_opposite_face=protect_opposite_face,
            face_ids=face_ids, a=self.a_capped, b=self.b_capped, a2=a, b2=b, element_key='cell')
        inst_cplr, cplr_refpoints = self.insert_cell(**cplr_params, align="port_a", align_to=start,
                                                     trans=pya.DCplxTrans(1, start_angle, False, 0, 0))

        # Spiral resonator
        if resonator_type == "twoface":
            res_params = {'connector_dist': connector_distance, "bridge_spacing": 0}
        elif resonator_type == "etched":
            res_params = {
                "airbridge_type": "Airbridge Multi Face",
                "include_bumps": False,
                "bridge_length": a + 2 * (b + self.etch_opposite_face_margin + extra_resonator_avoidance),
                "bridge_width": 2,
                "pad_length": 2,
                "bridge_spacing": self.bridge_spacing,
            }
        else:
            res_params = {"bridge_spacing": 0}

        inst_res, _ = self.insert_cell(
            SpiralResonatorPolygon,
            margin=self.margin + extra_resonator_avoidance,
            input_path=pya.DPath([
                pya.DPoint(0, 0),
            ], 10),
            poly_path=pya.DPath([
                pya.DPoint(self.cap_res_distance, 0),
                pya.DPoint(self.spiral_box_height, 0),
                pya.DPoint(self.spiral_box_height, -self.spiral_box_width),
                pya.DPoint(self.cap_res_distance, -self.spiral_box_width)
            ], 10),
            length=length,
            a=a,
            b=b,
            face_ids=face_ids,
            protect_opposite_face=protect_opposite_face,
            **res_params,
            inst_name=f'resonator{i}',
            trans=pya.DCplxTrans(1, start_angle, mirror, cplr_refpoints["port_b"])
        )

        # Top chip etching and grid avoidance above resonator
        if resonator_type == "etched":
            l0 = self.get_layer("ground_grid_avoidance", int(self.resonator_faces[0]))
            region = pya.Region(inst_res.cell.begin_shapes_rec(l0)).transformed(inst_res.trans)
            region += pya.Region(inst_cplr.cell.begin_shapes_rec(l0)).transformed(inst_cplr.trans)
            region = region.sized((self.etch_opposite_face_margin - self.margin) / self.layout.dbu)
            protection_region = region.sized(self.margin / self.layout.dbu)
            opposite_face = int(self.resonator_faces[1])
            self.cell.shapes(self.get_layer("ground_grid_avoidance", opposite_face)).insert(protection_region)
            self.cell.shapes(self.get_layer("base_metal_gap_wo_grid", opposite_face)).insert(region)
