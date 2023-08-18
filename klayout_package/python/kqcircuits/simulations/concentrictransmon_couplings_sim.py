# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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

from kqcircuits.qubits.concentric_transmon import ConcentricTransmon
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.simulations.port import InternalPort


@add_parameters_from(ConcentricTransmon, "*", junction_type="Sim", fluxline_type="none")
class ConcentricTransmonCouplingsSim(Simulation):
    qubit_faces = Param(pdt.TypeList, "List of faces", ["1t1", "2b1"])

    def build(self):

        # Translation between elements faces and port faces
        port_face = self.face_ids.index(self.qubit_faces[0])

        # Insert the qubit
        qubit_cell = self.add_element(ConcentricTransmon, **{**self.get_parameters(), 'face_ids': self.qubit_faces})
        qubit_trans = pya.DTrans(0, False, (self.box.left + self.box.right) / 2, (self.box.bottom + self.box.top) / 2)
        _, refp = self.insert_cell(qubit_cell, qubit_trans, rec_levels=None)

        # Add ports at the two islands
        if self.junction_type == 'Sim':
            self.ports.append(
                InternalPort(1, refp["port_squid_a"], face=port_face))
            self.ports.append(
                InternalPort(2, refp["port_squid_b"], face=port_face))

        # Add ports at the couplers
        for i in range(len(self.couplers_angle)):
            self.produce_waveguide_to_port(refp[f"port_coupler_{i+1}"], refp[f"port_coupler_{i+1}_corner"], i+3,
                                          'bottom', a=self.couplers_a[i], b=self.couplers_b[i], face=port_face)
