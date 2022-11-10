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


from kqcircuits.simulations.simulation import Simulation
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.chips.xmons_direct_coupling import XMonsDirectCoupling
from kqcircuits.simulations.port import InternalPort
from kqcircuits.elements.fluxlines.fluxline import Fluxline
from kqcircuits.junctions.junction import Junction


@add_parameters_from(Junction, junction_type="Sim")
@add_parameters_from(Fluxline, fluxline_type="none")
@add_parameters_from(XMonsDirectCoupling, "arm_width_a", "rr_cpl_width")
class XMonsDirectCouplingSim(Simulation):

    #Re-define some XMonsDirectCoupling parameters with defaults changed:
    qubit_spacing = Param(pdt.TypeDouble, "Qubit spacing", 3, unit="μm")
    arm_width_b = Param(pdt.TypeDouble, "Qubit 2 arm width", 66, unit="μm")
    waveguide_length = Param(pdt.TypeDouble,
                             "Length of waveguide stubs or distance between couplers and waveguide turning point", 100)
    cpl_width = Param(pdt.TypeDouble, "Qubit RR coupler width", 24, unit="μm")
    junction_inductances = Param(pdt.TypeList, "Qubit junction inductances",
                                [13.5e-9, 13.5e-9, 13.5e-9], unit="[H, H, H]")
    junction_capacitances = Param(pdt.TypeList, "Qubit junction capacitances",
                                [0.1e-15, 0.1e-15, 0.1e-15], unit="[F, F, F]")

    produce_qubits = XMonsDirectCoupling.produce_qubits

    def build(self):

        # parameter used by produce_qubits
        self.rr_cpl_width = (self.cpl_width, self.cpl_width, self.cpl_width)

        self.produce_qubits()

        # driveline 1
        self.produce_waveguide_to_port(
            port_nr=1,
            location=self.refpoints["QB1_port_drive"],
            side="left",
            term1=10,
            towards=self.refpoints["QB1_port_drive"] + pya.DVector(-1, 1)
        )
        # driveline 2
        self.produce_waveguide_to_port(
            port_nr=2,
            location=self.refpoints["QB2_port_drive"],
            side="bottom",
            term1=10,
            towards=self.refpoints["QB2_port_drive"] + pya.DVector(0, -1)
        )
        # driveline 3
        self.produce_waveguide_to_port(
            port_nr=3,
            location=self.refpoints["QB3_port_drive"],
            side="right",
            term1=10,
            towards=self.refpoints["QB3_port_drive"] + pya.DVector(1, 1),
        )

        # readout 1
        self.produce_waveguide_to_port(
            port_nr=4,
            a=5,
            b=20,
            location=self.refpoints["QB1_port_cplr1"],
            side="top",
            towards=self.refpoints["QB1_port_cplr1"] + pya.DVector(0, 1),
            use_internal_ports=True
        )
        # readout 2
        self.produce_waveguide_to_port(
            port_nr=5,
            a=5,
            b=20,
            location=self.refpoints["QB2_port_cplr1"],
            side="top",
            towards=self.refpoints["QB2_port_cplr1"] + pya.DVector(0, 1),
            use_internal_ports=True
        )
        # readout 3
        self.produce_waveguide_to_port(
            port_nr=6,
            a=5,
            b=20,
            location=self.refpoints["QB3_port_cplr1"],
            side="top",
            towards=self.refpoints["QB3_port_cplr1"] + pya.DVector(0, 1),
            use_internal_ports=True
        )

        # qubits
        self.ports.extend([
            InternalPort(7, *self.etched_line(self.refpoints["QB1_port_squid_a"], self.refpoints["QB1_port_squid_b"]),
                inductance=self.junction_inductances[0], capacitance=self.junction_capacitances[0], junction=True),
            InternalPort(8, *self.etched_line(self.refpoints["QB2_port_squid_a"], self.refpoints["QB2_port_squid_b"]),
                inductance=self.junction_inductances[1], capacitance=self.junction_capacitances[1], junction=True),
            InternalPort(9, *self.etched_line(self.refpoints["QB3_port_squid_a"], self.refpoints["QB3_port_squid_b"]),
                inductance=self.junction_inductances[2], capacitance=self.junction_capacitances[2], junction=True),
        ])
