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

from kqcircuits.chips.chip import Chip
from kqcircuits.defaults import default_airbridge_type
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter, t_cross_parameters
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.util.coupler_lib import cap_params
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node


class QualityFactor(Chip):
    """The PCell declaration for a QualityFactor chip."""
    res_lengths = Param(pdt.TypeList, "Resonator lengths", [5434, 5429, 5374, 5412, 5493, 5589], unit="[μm]",
                        docstring="Physical length of resonators [μm]")
    n_fingers = Param(pdt.TypeList, "Number of fingers of the coupler", [4, 4, 2, 4, 4, 4],
                      docstring="Fingers in planar capacitors")
    l_fingers = Param(pdt.TypeList, "Length of fingers", [23.1, 9.9, 14.1, 10, 21, 28], unit="[μm]",
                      docstring="Length of the capacitor fingers [μm]")
    type_coupler = Param(pdt.TypeList, "Coupler types",
                         ["interdigital", "interdigital", "interdigital", "gap", "gap", "gap"])
    n_ab = Param(pdt.TypeList, "Number of resonator airbridges", [5, 0, 5, 5, 5, 5])
    res_term = Param(pdt.TypeList, "Resonator termination type",
        ["galvanic", "galvanic", "galvanic", "airbridge", "airbridge", "airbridge"])
    res_beg = Param(pdt.TypeList, "Resonator beginning type",
        ["galvanic", "galvanic", "galvanic", "airbridge", "airbridge", "airbridge"])
    res_a = Param(pdt.TypeList, "Resonator waveguide center conductor width", [5, 10, 20, 5, 10, 20], unit="[μm]",
                  docstring="Width of the center conductor in the resonators [μm]")
    res_b = Param(pdt.TypeList, "Resonator waveguide gap width", [3, 6, 12, 3, 6, 12], unit="[μm]",
                  docstring="Width of the gap in the resonators [μm]")
    tl_airbridges = Param(pdt.TypeBoolean, "Airbridges on transmission line", True)
    res_airbridge_types = Param(pdt.TypeList, "Airbridge type for each resonator",
                         default=[default_airbridge_type]*6)
    launcher_top_dist = Param(pdt.TypeDouble, "Launcher distance from top", 2800, unit="μm")
    launcher_indent = Param(pdt.TypeDouble, "Launcher indentation from edge", 800, unit="μm")
    marker_safety = Param(pdt.TypeDouble, "Distance between launcher and first curve", 1000, unit="μm")
    feedline_bend_distance = Param(pdt.TypeDouble, "Horizontal distance of feedline bend", 100, unit="μm")
    resonators_both_sides = Param(pdt.TypeBoolean, "Place resonators on both sides of feedline", False)
    max_res_len = Param(pdt.TypeDouble, "Maximal straight length of resonators", 1e30, unit="μm",
                        docstring="Resonators exceeding this length become meandering")
    # override box to have hidden=False and allow GUI editing
    box = Param(pdt.TypeShape, "Border", pya.DBox(pya.DPoint(0, 0), pya.DPoint(10000, 10000)))

    def build(self):
        # Interpretation of parameter lists
        res_lengths = [float(foo) for foo in self.res_lengths]
        res_a = [float(foo) for foo in self.res_a]
        res_b = [float(foo) for foo in self.res_b]
        n_fingers = [float(foo) for foo in self.n_fingers]
        type_coupler = self.type_coupler
        n_ab = [int(foo) for foo in self.n_ab]
        l_fingers = [float(foo) for foo in self.l_fingers]
        res_term = self.res_term
        res_beg = self.res_beg

        # center the resonators in the chip regardless of size
        max_res_len = min(max(res_lengths), self.max_res_len)
        chip_side = self.box.p2.y - self.box.p1.y
        if self.resonators_both_sides:
            wg_top_y = chip_side / 2
        else:
            wg_top_y = (chip_side + max_res_len) / 2

        # Non-standard Launchers mimicking SMA8 at 1cm chip size, but keeping fixed distance from top
        launchers = self.produce_n_launchers(8, "RF", 300, 180, self.launcher_indent,
                                             chip_side - 2 * self.launcher_top_dist, {8: "PL-IN", 3: "PL-OUT"})

        # Define start and end of feedline
        points_fl = [launchers["PL-IN"][0]]
        if abs(launchers["PL-IN"][0].y - wg_top_y) > 1:
            # Bend in the feedline needed
            points_fl += [
                launchers["PL-IN"][0] + pya.DVector(self.r + self.marker_safety, 0),
                pya.DPoint(launchers["PL-IN"][0].x + self.r + self.feedline_bend_distance + self.marker_safety,
                           wg_top_y)
            ]
            points_fl_end = [
                pya.DPoint(launchers["PL-OUT"][0].x - self.r - self.feedline_bend_distance - self.marker_safety,
                           wg_top_y),
                launchers["PL-OUT"][0] + pya.DVector(-self.r - self.marker_safety, 0),
            ]
        elif self.marker_safety > 0:
            points_fl += [launchers["PL-IN"][0] + pya.DVector(self.marker_safety, 0)]
            points_fl_end = [
                launchers["PL-OUT"][0] + pya.DVector(-self.marker_safety, 0),
            ]
        else:
            points_fl_end = []

        points_fl_end += [launchers["PL-OUT"][0]]

        tl_start = points_fl[-1]
        tl_end = points_fl_end[0]

        resonators = len(self.res_lengths)
        v_res_step = (tl_end - tl_start) * (1. / resonators)
        cell_cross = self.add_element(WaveguideCoplanarSplitter, **t_cross_parameters(
            length_extra_side=2 * self.a, a=self.a, b=self.b, a2=self.a, b2=self.b))

        # Airbridge crossing resonators
        cell_ab_crossing = self.add_element(Airbridge)

        for i in range(resonators):
            resonator_up = self.resonators_both_sides and (i % 2) == 0

            # Cross
            cross_trans = pya.DTrans(0, resonator_up, tl_start + v_res_step * (i + 0.5))
            _, cross_refpoints_abs = self.insert_cell(cell_cross, cross_trans)

            # Coupler
            _, cplr_refpoints_abs = self.insert_cell(
                trans=pya.DTrans.R270 if resonator_up else pya.DTrans.R90,
                align="port_b",
                align_to=cross_refpoints_abs["port_bottom"],
                **cap_params(n_fingers[i], l_fingers[i], type_coupler[i], element_key='cell',
                             a=res_a[i], b=res_b[i], a2=self.a, b2=self.b)
            )

            pos_res_start = cplr_refpoints_abs["port_a"]
            sign = 1 if resonator_up else -1
            pos_res_end = pos_res_start + sign*pya.DVector(0, min(res_lengths[i], self.max_res_len))
            self.refpoints['resonator_{}_end'.format(i)] = pos_res_end

            # create resonator using WaveguideComposite
            if res_beg[i] == "airbridge":
                node_beg = Node(pos_res_start, AirbridgeConnection, with_side_airbridges=False)
            else:
                node_beg = Node(pos_res_start)

            length_increment = res_lengths[i] - self.max_res_len if res_lengths[i] > self.max_res_len else None
            bridge_length = res_a[i] + 2 * res_b[i] + 38
            if res_term[i] == "airbridge":
                node_end = Node(pos_res_end, AirbridgeConnection, with_side_airbridges=False,
                                with_right_waveguide=False, n_bridges=n_ab[i],
                                bridge_length=bridge_length, length_increment=length_increment)
            else:
                node_end = Node(pos_res_end, n_bridges=n_ab[i],
                                bridge_length=bridge_length, length_increment=length_increment)

            airbridge_type = default_airbridge_type
            if i < len(self.res_airbridge_types):
                airbridge_type = self.res_airbridge_types[i]
            wg = self.add_element(WaveguideComposite, nodes=[node_beg, node_end], a=res_a[i], b=res_b[i],
                airbridge_type=airbridge_type)
            self.insert_cell(wg)

            # Feedline
            self.insert_cell(WaveguideCoplanar, **{**self.cell.pcell_parameters_by_name(), **{
                "path": pya.DPath(points_fl + [
                    cross_refpoints_abs["port_left"]
                ], 1),
                "term2": 0
            }})
            points_fl = [cross_refpoints_abs["port_right"]]

            # airbridges on the left and right side of the couplers
            if self.tl_airbridges:
                ab_dist_to_coupler = 60.0
                ab_coupler_left = pya.DPoint((cross_refpoints_abs["port_left"].x) - ab_dist_to_coupler,
                                             (cross_refpoints_abs["port_left"].y))
                ab_coupler_right = pya.DPoint((cross_refpoints_abs["port_right"].x) + ab_dist_to_coupler,
                                              (cross_refpoints_abs["port_right"].y))

                self.insert_cell(cell_ab_crossing, pya.DTrans(0, False, ab_coupler_left))
                self.insert_cell(cell_ab_crossing, pya.DTrans(0, False, ab_coupler_right))

        # Last feedline

        self.insert_cell(WaveguideCoplanar, **{**self.cell.pcell_parameters_by_name(), **{
            "path": pya.DPath(points_fl + points_fl_end, 1),
            "term2": 0
        }})
