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


import math

from kqcircuits.chips.chip import Chip
from kqcircuits.qubits.qubit import Qubit
from kqcircuits.qubits.swissmon import Swissmon
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node
from kqcircuits.elements.waveguide_coplanar_taper import WaveguideCoplanarTaper
from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter, t_cross_parameters
from kqcircuits.pya_resolver import pya
from kqcircuits.util.coupler_lib import cap_params
from kqcircuits.util.parameters import Param, pdt, add_parameters_from


@add_parameters_from(Qubit, "junction_type", "fluxline_type")
class XMonsDirectCoupling(Chip):
    """The PCell declaration for an XMonsDirectCoupling chip."""

    qubit_spacing = Param(pdt.TypeDouble, "Qubit spacing", 10, unit="μm")
    arm_width_a = Param(pdt.TypeDouble, "Qubit 1 and 3 arm width", 24, unit="μm")
    arm_width_b = Param(pdt.TypeDouble, "Qubit 2 arm width", 24, unit="μm")
    rr_cpl_width = Param(pdt.TypeList, "RR to QB coupler width (um for each RR)", [24, 24, 24])

    def produce_readout_resonator(self, pos_start, end_y, length, name, c_kappa_l_fingers):
        # 86 ohms
        ro_a = 5
        ro_b = 20

        taper_length = 100

        # T to PL
        _, pl_cross_ref = self.insert_cell(WaveguideCoplanarSplitter,
            pya.DTrans(pos_start.x, end_y),
            inst_name=("PL{}".format(name) if name else None),
            label_trans=pya.DTrans.R90,
            **t_cross_parameters(a=self.a, b=self.b, a2=self.a, b2=self.b, length_extra_side=20, length_extra=0)
        )

        # Finger cap
        cplr_cell = self.add_element(**cap_params(4, c_kappa_l_fingers, "interdigital"))
        cplr_ref_rel = self.get_refpoints(cplr_cell, pya.DTrans.R90)
        _, cplr_ref = self.insert_cell(
            cplr_cell, pya.DTrans(pl_cross_ref["port_bottom"]-cplr_ref_rel["port_b"])*pya.DTrans.R90)

        # Taper to T
        taper_cell, taper_ref_rel = WaveguideCoplanarTaper.create_with_refpoints(
            self.layout, self.LIBRARY_NAME, pya.DTrans.R90,
            a=ro_a,
            b=ro_b,
            a2=self.a,
            b2=self.b,
            taper_length=taper_length
        )
        _, taper_ref = self.insert_cell(
            taper_cell, pya.DTrans(cplr_ref["port_a"]-taper_ref_rel["port_b"])*pya.DTrans.R90)

        # T to tail and straight
        rr_cross_cell = self.add_element(WaveguideCoplanarSplitter, **t_cross_parameters(
            length_extra_side=40,
            length_extra=0,
            a=ro_a,
            b=ro_b,
            a2=ro_a,
            b2=ro_b,
        ))
        rr_cross_ref_rel = self.get_refpoints(rr_cross_cell, pya.DTrans.R90)
        _, rr_cross_ref = self.insert_cell(
            rr_cross_cell, pya.DTrans(taper_ref["port_a"]-rr_cross_ref_rel["port_right"])*pya.DTrans.R90)

        # straight
        self.insert_cell(WaveguideComposite,
            nodes=[
                Node(rr_cross_ref["port_left"]),
                Node(pos_start, n_bridges=10),
            ],
            a=ro_a,
            b=ro_b,
        )

        # tail
        non_tail_length = (rr_cross_ref["base"]-pos_start).length()
        tail_r = 100
        tail_v = pya.DVector(0, -(length
                                  - non_tail_length  # straight down
                                  - (rr_cross_ref["base"]-rr_cross_ref["port_bottom"]).length()  # t-piece
                                  - math.pi/2*tail_r  # curve
                                  + tail_r  # vertical offset for the straight part with fixed length
                                  ))
        self.insert_cell(WaveguideComposite,
            nodes=[
                Node(rr_cross_ref["port_bottom"]),
                Node(rr_cross_ref["port_bottom_corner"]),
                Node(rr_cross_ref["port_bottom_corner"]+tail_v, n_bridges=5),
            ],
            a=ro_a,
            b=ro_b,
            r=tail_r
        )

    def produce_qubits(self):
        """A dedicated function to be used also by the corresponding simulation object.

        Assumes following attributes:

        * arm_width_a
        * arm_width_b
        * qubit_spacing
        * fluxline_type
        * rr_cpl_width
        * junction_type
        * layout
        * insert_cell
        """

        # Finnmon
        arm_length = 146
        qubit_props_common = {
            "arm_length": [arm_length] * 4,
            "island_r": 2,
            "port_width": [10, 5, 10],
        }
        arm_width_a = self.arm_width_a
        arm_width_b = self.arm_width_b
        full_gap_width = 72
        qb1_coupler_width, qb2_coupler_width, qb3_coupler_width = [float(param) for param in self.rr_cpl_width]
        finnmon_1 = self.add_element(Swissmon,
            arm_width=[arm_width_a] * 4,
            gap_width=[(full_gap_width - arm_width_a) / 2] * 4,
            cpl_gap=[110, 90, 110],
            cpl_length=[0, 134+qb1_coupler_width, 0],
            cpl_width=[60, qb1_coupler_width, 60],
            cl_offset=[150, -150],
            **qubit_props_common)
        finnmon_2 = self.add_element(Swissmon,
            arm_width=[arm_width_b] * 4,
            gap_width=[(full_gap_width - arm_width_b) / 2] * 4,
            cpl_gap=[110, 102, 110],
            cpl_length=[0, 116+qb2_coupler_width, 0],
            cpl_width=[60, qb2_coupler_width, 60],
            cl_offset=[150, 150],
            **qubit_props_common)
        finnmon_3 = self.add_element(Swissmon,
            arm_width=[arm_width_a]*4,
            gap_width=[(full_gap_width - arm_width_a) / 2] * 4,
            cpl_gap=[110, 90, 110],
            cpl_length=[0, 134+qb3_coupler_width, 0],
            cpl_width=[60, qb3_coupler_width, 60],
            cl_offset=[-150, -150],
            **qubit_props_common)

        qubit_y = 5e3
        qubit_step = ((full_gap_width-arm_width_a)/2+(full_gap_width-arm_width_b)/2)+2*arm_length
        self.insert_cell(finnmon_1,
                         trans=pya.DTrans(5e3 - qubit_step - self.qubit_spacing, qubit_y),
                         inst_name="QB1",
                         label_trans=pya.DTrans.R90,
                         rec_levels=None)
        self.insert_cell(finnmon_2,
                         trans=pya.DTrans(5e3, qubit_y),
                         inst_name="QB2",
                         label_trans=pya.DTrans.R90,
                         rec_levels=None
                         )
        self.insert_cell(finnmon_3,
                         trans=pya.DTrans(5e3 + qubit_step + self.qubit_spacing, qubit_y),
                         inst_name="QB3",
                         label_trans=pya.DTrans.R90,
                         rec_levels=None
                         )

    def build(self):

        self.produce_launchers("SMA8")
        self.produce_junction_tests(junction_type=self.junction_type)
        self.produce_qubits()

        # Readout resonators
        height_rr_feedline = 7.9e3
        # target parameters V2
        self.produce_readout_resonator(
            self.refpoints["QB1_port_cplr1"], height_rr_feedline, 2421.5 + 2447.1, name="1",
            c_kappa_l_fingers=60.8
        )
        self.produce_readout_resonator(
            self.refpoints["QB2_port_cplr1"], height_rr_feedline, 2436 + 2246.3, name="2",
            c_kappa_l_fingers=61.55
        )
        self.produce_readout_resonator(
            self.refpoints["QB3_port_cplr1"], height_rr_feedline, 2438.5 + 2248.2, name="3",
            c_kappa_l_fingers=58.1
        )

        # PL input cap
        pl_in_cap_cell = self.add_element(**cap_params(8, 55.4))  # 35 fF
        pl_in_cap_ref_rel = self.get_refpoints(pl_in_cap_cell)
        pl_in_cap_trans = pya.DTrans(
            pya.DPoint(self.refpoints["QB1_port_cplr1"].x - 300, height_rr_feedline) - pl_in_cap_ref_rel["port_b"])
        self.insert_cell(pl_in_cap_cell, pl_in_cap_trans, inst_name="IN")
        # Transmission lines
        tl_gap = 300
        # RR feedline
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["NW_port"]),
            Node((self.refpoints["NW_port"].x, height_rr_feedline)),
            Node(self.refpoints["IN_port_a"], n_bridges=3),
        ])
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["IN_port_b"]),
            Node(self.refpoints["PL1_port_left"], n_bridges=1),
        ])
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["PL1_port_right"]),
            Node(self.refpoints["PL2_port_left"], n_bridges=1),
        ])
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["PL2_port_right"]),
            Node(self.refpoints["PL3_port_left"], n_bridges=1),
        ])
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["PL3_port_right"]),
            Node((self.refpoints["NE_port"].x, height_rr_feedline), n_bridges=4),
            Node(self.refpoints["NE_port"]),
        ])
        # Qb1 driveline
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["WN_port"]),
            Node((self.refpoints["NW_port"].x - tl_gap, self.refpoints["WN_port"].y)),
            Node(self.refpoints["QB1_port_drive"], n_bridges=25)
        ], term2=self.b)
        # Qb1 fluxline
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["WS_port"]),
            Node(self.refpoints["WS_port_corner"]),
            Node(self.refpoints["QB1_port_flux_corner"], n_bridges=30),
            Node(self.refpoints["QB1_port_flux"])
        ])
        # Qb2 driveline
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["SW_port"]),
            Node((self.refpoints["SW_port"].x, self.refpoints["WS_port"].y - tl_gap)),
            Node(self.refpoints["QB2_port_drive"] + pya.DPoint(0, -3*self.r), n_bridges=30),
            Node(self.refpoints["QB2_port_drive"])
        ], term2=self.b)
        # Qb2 fluxline
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["SE_port"]),
            Node((self.refpoints["SE_port"].x, self.refpoints["ES_port"].y - tl_gap)),
            Node(self.refpoints["QB2_port_flux_corner"], n_bridges=30),
            Node(self.refpoints["QB2_port_flux"])
        ])
        # Qb3 driveline
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["EN_port"]),
            Node((self.refpoints["NE_port"].x + tl_gap, self.refpoints["EN_port"].y)),
            Node(self.refpoints["QB3_port_drive"], n_bridges=25)
        ], term2=self.b)
        # Qb3 fluxline
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["ES_port"]),
            Node(self.refpoints["ES_port_corner"]),
            Node(self.refpoints["QB3_port_flux_corner"], n_bridges=30),
            Node(self.refpoints["QB3_port_flux"])
        ])
