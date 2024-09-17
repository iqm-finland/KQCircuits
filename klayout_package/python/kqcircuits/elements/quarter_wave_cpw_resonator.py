# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter, t_cross_parameters
from kqcircuits.util.coupler_lib import cap_params
from kqcircuits.util.refpoints import WaveguideToSimPort
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.defaults import default_airbridge_type
from kqcircuits.elements.airbridges import airbridge_type_choices


class QuarterWaveCpwResonator(Element):
    """
    CPW Resonator
    """

    probeline_length = Param(pdt.TypeDouble, "Probeline length", 500, unit="μm")
    resonator_length = Param(pdt.TypeDouble, "Resonator length ", 1000, unit="μm")
    max_res_len = Param(
        pdt.TypeDouble,
        "Maximal straight length of resonators",
        1e30,
        unit="μm",
        docstring="Resonators exceeding this length become meandering",
    )
    res_beg = Param(pdt.TypeString, "Resonator beginning type", "galvanic")
    res_term = Param(pdt.TypeString, "Resonator termination type", "galvanic")
    n_ab = Param(pdt.TypeInt, "Number of resonator airbridges", 0)
    res_airbridge_type = Param(
        pdt.TypeString, "Airbridge type", default=default_airbridge_type, choices=airbridge_type_choices
    )
    tl_airbridges = Param(pdt.TypeBoolean, "Airbridges on transmission line", True)
    n_fingers = Param(pdt.TypeDouble, "Number of fingers", 1, unit="")
    l_fingers = Param(pdt.TypeDouble, "Finger length", 1, unit="")
    ground_grid_in_trace = Param(pdt.TypeBoolean, "Include ground-grid in the trace", False)

    type_coupler = Param(
        pdt.TypeString,
        "Capacitor coupler type",
        "smooth",
        choices=[
            ["Interdigital", "interdigital"],
            ["Gap", "gap"],
            ["Smooth", "smooth"],
            ["Ground gap", "ground gap"],
        ],
    )

    res_a = Param(pdt.TypeDouble, "Trace width of resonator line", 10, unit="μm")
    res_b = Param(pdt.TypeDouble, "Gap width of resonator line", 10, unit="μm")

    use_internal_ports = Param(pdt.TypeBoolean, "Internal ports (EPR)", False)

    def build(self):

        cell_cross = self.add_element(
            WaveguideCoplanarSplitter,
            **t_cross_parameters(
                length_extra_side=2 * self.a,
                a=self.a,
                b=self.b,
                a2=self.a,
                b2=self.b,
            ),
        )

        cell_ab_crossing = self.add_element(Airbridge)

        # Cross
        _, cross_refpoints_abs = self.insert_cell(cell_cross)

        points_pl1 = [pya.DPoint(-self.probeline_length / 2.0, 0)]
        points_pl1 += [cross_refpoints_abs["port_left"]]

        points_pl2 = [cross_refpoints_abs["port_right"]]
        points_pl2 += [pya.DPoint(self.probeline_length / 2.0, 0)]

        # Coupler
        _, cplr_refpoints_abs = self.insert_cell(
            trans=pya.DTrans.R90,
            align="port_b",
            align_to=cross_refpoints_abs["port_bottom"],
            **cap_params(
                self.n_fingers,
                self.l_fingers,
                self.type_coupler,
                element_key="cell",
                a=self.res_a,
                b=self.res_b,
                a2=self.a,
                b2=self.b,
            ),
        )

        pos_res_start = cplr_refpoints_abs["port_a"]
        pos_res_end = pos_res_start - pya.DVector(0, min(self.resonator_length, self.max_res_len))

        # create resonator using WaveguideComposite
        if self.res_beg == "airbridge":
            node_beg = Node(pos_res_start, AirbridgeConnection, with_side_airbridges=False)
        else:
            node_beg = Node(pos_res_start)

        length_increment = (
            self.resonator_length - self.max_res_len if self.resonator_length > self.max_res_len else None
        )

        bridge_approach = 38.0
        bridge_length = self.res_a + 2 * self.res_b + bridge_approach

        if self.res_term == "airbridge":
            node_end = Node(
                pos_res_end,
                AirbridgeConnection,
                with_side_airbridges=False,
                with_right_waveguide=False,
                n_bridges=self.n_ab,
                bridge_length=bridge_length,
                length_increment=length_increment,
            )
        else:
            node_end = Node(
                pos_res_end, n_bridges=self.n_ab, bridge_length=bridge_length, length_increment=length_increment
            )

        airbridge_type = self.res_airbridge_type
        resonator_element = self.add_element(
            WaveguideComposite,
            nodes=[node_beg, node_end],
            a=self.res_a,
            b=self.res_b,
            ground_grid_in_trace=self.ground_grid_in_trace,
            airbridge_type=airbridge_type,
        )

        cells_pl1, _ = self.insert_cell(WaveguideCoplanar, path=points_pl1)
        cells_pl2, _ = self.insert_cell(WaveguideCoplanar, path=points_pl2)
        cells_resonator, _ = self.insert_cell(resonator_element)

        # airbridges on the left and right side of the couplers
        if self.tl_airbridges:
            ab_dist_to_coupler = 60.0
            ab_coupler_left = pya.DPoint(
                (cross_refpoints_abs["port_left"].x) - ab_dist_to_coupler, (cross_refpoints_abs["port_left"].y)
            )
            ab_coupler_right = pya.DPoint(
                (cross_refpoints_abs["port_right"].x) + ab_dist_to_coupler, (cross_refpoints_abs["port_right"].y)
            )

            self.insert_cell(cell_ab_crossing, pya.DTrans(0, False, ab_coupler_left))
            self.insert_cell(cell_ab_crossing, pya.DTrans(0, False, ab_coupler_right))

        self.copy_port("a", cells_pl1)
        self.copy_port("b", cells_pl2)
        self.copy_port("b", cells_resonator, "resonator_b")

    @classmethod
    def get_sim_ports(cls, simulation):
        return [
            WaveguideToSimPort(
                "port_a", use_internal_ports=simulation.use_internal_ports, a=simulation.a, b=simulation.b
            ),
            WaveguideToSimPort(
                "port_b", use_internal_ports=simulation.use_internal_ports, a=simulation.a, b=simulation.b
            ),
            WaveguideToSimPort("port_resonator_b", a=simulation.res_a, b=simulation.res_b),
        ]
