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
from kqcircuits.chips.chip import Chip
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.qubits.swissmon import Swissmon
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter, t_cross_parameters
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare



class Simple(Chip):
    """The PCell declaration for a very simple chip.

       Contains a small number of elements connected in a simple, direct way.
    """

    name_chip = Param(pdt.TypeString, "Name of the chip", "Simple")

    def build(self):

        # Launcher
        launchers = self.produce_launchers("SMA8", enabled=["WN", "EN", "SE"])

        # Swissmon
        _pos = pya.DTrans(3, False, 2500, launchers["WN"][0].y)
        _, swissmon_refs = self.insert_cell(Swissmon, _pos, cpl_length=[0, 150, 0])

        # Two FingerCapacitorSquare instances
        cap_cell = self.add_element(FingerCapacitorSquare, finger_width=20, finger_length=100, finger_number=7)
        _, cap1_refs = self.insert_cell(cap_cell, pya.DTrans(5000.0, launchers["WN"][0].y), "C1")
        self.insert_cell(cap_cell, pya.DTrans(3, False, launchers["SE"][0].x, 5000.0), "C2")

        # WaveguideCoplanarSplitter
        _pos = pya.DTrans(launchers["SE"][0].x, launchers["WN"][0].y)
        _, tcross_refs = self.insert_cell(WaveguideCoplanarSplitter, _pos, **t_cross_parameters(
            a=self.a, b=self.b, a2=self.a, b2=self.b))

        # Waveguides: WN -> Swissmon -> FingerCapacitorSquare -> WaveguideCoplanarSplitter -> EN
        self.insert_cell(WaveguideCoplanar, path=pya.DPath([launchers["WN"][0], swissmon_refs["port_flux"]], 1))
        self.insert_cell(WaveguideCoplanar, path=pya.DPath([swissmon_refs["port_cplr1"], cap1_refs["port_a"]], 1))
        self.insert_cell(WaveguideCoplanar, path=pya.DPath([cap1_refs["port_b"], tcross_refs["port_left"]], 1))
        self.insert_cell(WaveguideCoplanar, path=pya.DPath([tcross_refs["port_right"], launchers["EN"][0]], 1))

        # Waveguides: TCross' bottom -> second capacitor -> SE
        refs = self.refpoints
        self.insert_cell(WaveguideCoplanar, path=pya.DPath([tcross_refs["port_bottom"], refs["C2_port_a"]], 1))
        self.insert_cell(WaveguideCoplanar, path=pya.DPath([refs["C2_port_b"], launchers["SE"][0]], 1))
