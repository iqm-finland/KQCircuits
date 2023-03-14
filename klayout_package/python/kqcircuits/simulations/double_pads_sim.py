# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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
from kqcircuits.simulations.port import InternalPort
from kqcircuits.qubits.double_pads import DoublePads
from kqcircuits.util.parameters import Param, pdt, add_parameters_from

@add_parameters_from(DoublePads)
class DoublePadsSim(Simulation):

    qubit_face = Param(pdt.TypeList, "Bottom or top face qubit position", ['1t1', '2b1'])
    internal_island_ports = Param(pdt.TypeBoolean, "Add InternalPorts on both islands. Use for capacitive simulations.",
                                False)
    junction_inductance = Param(pdt.TypeList, "Qubit junction inductance",
                                11.497e-9, unit="H")
    junction_capacitance = Param(pdt.TypeList, "Qubit junction capacitance",
                                0.1e-15, unit="F")

    def build(self):
        double_pads_cell = self.add_element(DoublePads,
            **{**self.get_parameters(), "junction_type": "Sim", 'face_ids': self.qubit_face})

        qubit_trans = pya.DTrans(0, False, (self.box.left + self.box.right) / 2, (self.box.bottom + self.box.top) / 2)
        _, refp = self.insert_cell(double_pads_cell, qubit_trans, rec_levels=None)

        # translation between elements faces and port faces
        port_face = self.face_ids.index(self.qubit_face[0])

        # Add ports
        port_i = 0
        if self.internal_island_ports:
            self.ports.extend((
                InternalPort((port_i := port_i + 1), refp["port_squid_a"], face=port_face),
                InternalPort((port_i := port_i + 1), refp["port_squid_b"], face=port_face),
            ))
        else:  # Junction between the islands
            self.ports.append(
                InternalPort((port_i := port_i + 1), *self.etched_line(refp["port_squid_a"], refp["port_squid_b"]),
                    face=port_face, inductance=self.junction_inductance, capacitance=self.junction_capacitance,
                    junction=True
                )
            )

        self.produce_waveguide_to_port(refp["port_cplr"], refp["port_cplr_corner"], (port_i := port_i + 1),
            "top", waveguide_length=self.waveguide_length, face=port_face)
