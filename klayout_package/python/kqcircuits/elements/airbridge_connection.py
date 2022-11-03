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


from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_taper import WaveguideCoplanarTaper
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from


@add_parameters_from(Airbridge)
@add_parameters_from(WaveguideCoplanarTaper, "*", m2=5)
class AirbridgeConnection(Element):
    """The PCell declaration of an Airbridge with tapered waveguides in both ends.

     .. MARKERS_FOR_PNG 0,20 23,26 14,-15
    """

    bridge_gap_width = Param(pdt.TypeDouble, "Width of waveguide gap around the Airbridge", 12, unit="μm")
    with_side_airbridges = Param(pdt.TypeBoolean, "With airbridges on the sides", True)
    with_right_waveguide = Param(pdt.TypeBoolean, "With waveguide on right side", True)
    gap_between_bridges = Param(pdt.TypeDouble, "Inner distance between adjacent bridges", 20)
    waveguide_extra = Param(pdt.TypeDouble, "Waveguide extra length below airbridge", 0)

    def build(self):
        # Add airbridges
        ab = self.add_element(Airbridge)
        ab_inst, ab_ref = self.insert_cell(ab, pya.DTrans.R90)
        if self.with_side_airbridges:
            self.insert_cell(ab, pya.DTrans(1, False, 0,  self.bridge_width + self.gap_between_bridges))
            self.insert_cell(ab, pya.DTrans(1, False, 0, -self.bridge_width - self.gap_between_bridges))

        # Add left waveguide
        pad_a = self.bridge_width
        pad_b = self.bridge_gap_width
        wg_l_pos = ab_ref["port_a"] + pya.DVector(self.waveguide_extra, 0)
        taper_l_pos = ab_ref["port_a"] - pya.DVector(self.pad_length, 0)
        terminator_l = self.add_element(WaveguideCoplanar,
                                        path=[taper_l_pos, wg_l_pos],
                                        a=pad_a, b=pad_b,
                                        term1=0, term2=pad_b)
        self.insert_cell(terminator_l, pya.DTrans(0, 0))

        taper_l = self.add_element(WaveguideCoplanarTaper, a2=pad_a, b2=pad_b)
        taper_l_ref = self.get_refpoints(taper_l)
        taper_l_inst, _ = self.insert_cell(taper_l, pya.DTrans(taper_l_pos-taper_l_ref["port_b"].to_v()))
        self.copy_port("a", taper_l_inst)

        # Optionally, add right waveguide
        if self.with_right_waveguide:
            wg_r_pos = ab_ref["port_b"] - pya.DVector(self.waveguide_extra, 0)
            taper_r_pos = ab_ref["port_b"] + pya.DVector(self.pad_length, 0)
            terminator_r = self.add_element(WaveguideCoplanar,
                                            path=[wg_r_pos, taper_r_pos],
                                            a=pad_a, b=pad_b,
                                            term1=pad_b, term2=0)
            self.insert_cell(terminator_r, pya.DTrans(0, 0))

            taper_r = self.add_element(WaveguideCoplanarTaper, a=pad_a, b=pad_b)
            taper_r_ref = self.get_refpoints(taper_r)
            taper_r_inst, _ = self.insert_cell(taper_r, pya.DTrans(taper_r_pos-taper_r_ref["port_a"].to_v()))
            self.copy_port("b", taper_r_inst)
        else:
            wg_r_pos = ab_ref["port_b"]
            self.copy_port("b", ab_inst)

        # Add path
        path_airbridge = pya.DPath([wg_l_pos, wg_r_pos], self.bridge_width)
        self.cell.shapes(self.get_layer("waveguide_length")).insert(path_airbridge)
