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
from kqcircuits.qubits.swissmon import Swissmon
from kqcircuits.util.parameters import Param, pdt, add_parameters_from

@add_parameters_from(Swissmon)
class SingleXmon(Simulation):

    qubit_face = Param(pdt.TypeList, "Bottom or top face qubit position", ['2b1', '1t1'])
    junction_inductance = Param(pdt.TypeList, "Qubit junction inductance",
                                11.497e-9, unit="H")
    junction_capacitance = Param(pdt.TypeList, "Qubit junction capacitance",
                                0.1e-15, unit="F")

    def build(self):
        xmon_cell = self.add_element(Swissmon,
            **{**self.get_parameters(), "junction_type": "Sim", "fluxline_type": "none",
               'face_ids': self.qubit_face})

        qubit_trans = pya.DTrans(0, False, (self.box.left + self.box.right) / 2, (self.box.bottom + self.box.top) / 2)
        _, refp = self.insert_cell(xmon_cell, qubit_trans, rec_levels=None)

        # translation between elements faces and port faces
        port_face = self.face_ids.index(self.qubit_face[0])

        # Add port geometry and definitions
        self.ports.append(
            InternalPort(
                1,
                *self.etched_line(refp["port_squid_a"], refp["port_squid_b"]),
                face=port_face,
                inductance=self.junction_inductance,
                capacitance=self.junction_capacitance,
                junction=True,
            )
        )
