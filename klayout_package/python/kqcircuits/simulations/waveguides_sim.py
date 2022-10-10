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
from kqcircuits.simulations.port import EdgePort
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.flip_chip_connectors.flip_chip_connector_dc import FlipChipConnectorDc


class WaveGuidesSim(Simulation):

    cpw_length = Param(pdt.TypeDouble, "Waveguide length", 100, unit="μm")
    n_guides = Param(pdt.TypeInt, "Number of guides", 5)
    spacing = Param(pdt.TypeDouble, "Parallel spacing", 100, unit="μm")
    guide_face_id = Param(pdt.TypeString, "Guide face id", '1t1')
    add_bumps = Param(pdt.TypeBoolean, "Add ground bumps", False)
    port_termination_end = Param(pdt.TypeBoolean, "Port termination end", True)
    use_edge_ports = Param(pdt.TypeBoolean, "Use edge ports", True)

    def build(self):
        self.produce_guides()
        if self.add_bumps:
            self.produce_ground_bumps()

    def produce_guides(self):
        cpw_length = self.cpw_length
        n_guides = self.n_guides
        a = self.a
        b = self.b
        spacing = self.spacing
        tot_y = (n_guides-1)*spacing
        guide_face_id = self.guide_face_id
        face_id = {
            '1t1': 0,
            '2b1': 1
        }

        for i in range(n_guides):
            y_pos = i*spacing-tot_y/2.
            p1 = pya.DPoint(-cpw_length/2, y_pos)
            p2 = pya.DPoint(cpw_length/2., y_pos)
            p0 = pya.DPoint(0, y_pos)
            # waveguide_cell = self.add_element(WaveguideCoplanar, path=pya.DPath([p1, p2], 0),
            #                                   face_ids=[guide_face_id])
            if self.use_edge_ports:
                wg_cell = self.add_element(WaveguideCoplanar, path=pya.DPath([p1, p2], 0), term1=0,
                                           term2=0, face_ids=[guide_face_id])
                self.insert_cell(wg_cell)
                self.ports.append(EdgePort(i + 1, p1, face=face_id[guide_face_id]))
            else:
                if self.port_termination_end:
                    self.produce_waveguide_to_port(p0, p1, 2*i, waveguide_length=cpw_length/2.,
                                                   a=a, b=b, face=face_id[guide_face_id])
                    self.produce_waveguide_to_port(p0, p2, 2*i+1, waveguide_length=cpw_length/2.,
                                                   a=a, b=b, face=face_id[guide_face_id])
                else:
                    self.produce_waveguide_to_port(p0, p1, i, waveguide_length=cpw_length/2.,
                                                   a=a, b=b, face=face_id[guide_face_id])
                    wg_cell = self.add_element(WaveguideCoplanar, path=pya.DPath([p0, p2], 0), term1=0,
                                               term2=self.b, face_ids=[guide_face_id])
                    self.insert_cell(wg_cell)

    def produce_ground_bumps(self):
        n_guides = self.n_guides
        spacing = self.spacing
        tot_y = (n_guides-1)*spacing
        bump = self.add_element(FlipChipConnectorDc)

        for i in range(n_guides-1):
            y_pos = i*spacing-tot_y/2.+spacing/2.
            self.insert_cell(bump, pya.DCplxTrans(1, 0, False, pya.DVector(0, y_pos)))
