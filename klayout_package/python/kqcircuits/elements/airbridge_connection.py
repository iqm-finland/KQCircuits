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


from kqcircuits.elements.airbridges import airbridge_type_choices
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.airbridges.airbridge_rectangular import AirbridgeRectangular
from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_taper import WaveguideCoplanarTaper
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from


@add_parameters_from(Airbridge)
@add_parameters_from(AirbridgeRectangular, "bridge_width")
@add_parameters_from(WaveguideCoplanarTaper)
class AirbridgeConnection(Element):
    """The PCell declaration of an Airbridge with tapered waveguides in both ends."""

    with_side_airbridges = Param(pdt.TypeBoolean, "With airbridges on the sides", True)
    with_right_waveguide = Param(pdt.TypeBoolean, "With waveguide on right side", True)
    waveguide_separation = Param(pdt.TypeDouble, "Distance between waveguide center conductors", 60)
    airbridge_type = Param(pdt.TypeString, "Airbridge type", Airbridge.default_type, choices=airbridge_type_choices)

    def produce_impl(self):
        taper_l = self.add_element(WaveguideCoplanarTaper, WaveguideCoplanarTaper,
            a2=self.bridge_width,
            b2=self.bridge_width/self.a * self.b
        )
        taper_l_ref = self.get_refpoints(taper_l)
        taper_end_v = pya.DVector(-self.bridge_length/2-2*self.pad_length, 0)
        _, taper_l_ref_abs = self.insert_cell(taper_l, pya.DTrans(taper_end_v-taper_l_ref["port_b"].to_v()))

        a = self.bridge_width
        b = a/self.a * self.b
        terminator_l = self.add_element(WaveguideCoplanar,
            face_ids=self.face_ids,
            path=pya.DPath([
                taper_end_v.to_p(),
                pya.DPoint(-self.waveguide_separation/2, 0)
            ], 10),
            a=a,
            b=b,
            term1=0,
            term2=b
        )
        self.insert_cell(terminator_l, pya.DTrans(0, 0))

        ab = self.add_element(Airbridge, Airbridge, airbridge_type=self.airbridge_type)
        self.insert_cell(ab, pya.DTrans.R90)
        if self.with_side_airbridges:
            gap_between_bridges = 20
            self.insert_cell(ab, pya.DTrans(1, False, 0,  self.bridge_width + gap_between_bridges))
            self.insert_cell(ab, pya.DTrans(1, False, 0, -self.bridge_width - gap_between_bridges))

        if self.with_right_waveguide:
            taper_r = self.add_element(WaveguideCoplanarTaper, WaveguideCoplanarTaper,
                a1=self.bridge_width,
                b1=self.bridge_width/self.a * self.b
            )
            taper_r_ref = self.get_refpoints(taper_r)
            taper_end_v = pya.DVector(self.bridge_length/2+2*self.pad_length, 0)
            _, taper_r_ref_abs = self.insert_cell(taper_r, pya.DTrans(taper_end_v-taper_r_ref["port_a"].to_v()))

            terminator_r = self.add_element(WaveguideCoplanar,
                face_ids=self.face_ids,
                path=pya.DPath([
                    pya.DPoint(self.waveguide_separation/2, 0),
                    taper_end_v.to_p(),
                ], 10),
                a=a,
                b=b,
                term1=b,
                term2=0
            )
            self.insert_cell(terminator_r, pya.DTrans(0, 0))

        self.add_port("a", taper_l_ref_abs["port_a"])
        if self.with_right_waveguide:
            self.add_port("b", taper_r_ref_abs["port_b"])

        path_airbridge = pya.DPath([pya.DPoint(-self.waveguide_separation/2, 0),
                                    pya.DPoint(self.waveguide_separation/2, 0)], self.bridge_width)
        self.cell.shapes(self.get_layer("waveguide_length")).insert(path_airbridge)

        # adds annotation based on refpoints calculated above
        super().produce_impl()
