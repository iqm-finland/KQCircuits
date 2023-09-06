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
from math import sqrt
from kqcircuits.util.parameters import Param, pdt, add_parameters_from, pya
from kqcircuits.elements.element import Element

from kqcircuits.elements.waveguide_composite import WaveguideComposite
from kqcircuits.elements.waveguide_composite import Node
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter
from kqcircuits.elements.finger_capacitor_taper import FingerCapacitorTaper
from kqcircuits.util.refpoints import RefpointToEdgePort

@add_parameters_from(FingerCapacitorSquare, finger_gap_end=3)
@add_parameters_from(FingerCapacitorTaper, finger_width=10, finger_number=2, finger_gap=3)
class CapacitiveXCoupler(Element):
    """
    Capacitive coupler for testing FEM computations.
    """
    x_coupler_length = Param(pdt.TypeDouble, "Length of Capacitive X Coupler", 500)
    x_coupler_height = Param(pdt.TypeDouble, "Height of Capacitive X Coupler", 500)
    x_coupler_variant = Param(pdt.TypeString, "Coupler variant, either (+) or (x)", "+", choices=["+", "x"])
    remove_capacitors = Param(pdt.TypeBoolean, "Remove capacitors from the X Coupler", False)


    def build(self):
        length = self.x_coupler_length
        height = self.x_coupler_height
        if length>height:
            center = height
            input_length = (length-center)/2.
        else:
            center = length
            input_length = (height-center)/2.

        p0 = (0,0)

        if self.x_coupler_variant == "x":
            if height > length:
                p11 = (-center/2., -input_length-length/2.)
                p12 = (-length/2., -center/2.)
                p13 = (-length/4., -center/4.)
            else:
                p11 = (-input_length-center/2., -height/2.)
                p12 = (-center/2., -height/2.)
                p13 = (-center/4., -height/4.)

            p21 = (-p11[0], p11[1])
            p22 = (-p12[0], p12[1])
            p23 = (-p13[0], p13[1])

            p31 = (-p11[0],-p11[1])
            p32 = (-p12[0],-p12[1])
            p33 = (-p13[0],-p13[1])

            p41 = ( p11[0],-p11[1])
            p42 = ( p12[0],-p12[1])
            p43 = ( p13[0],-p13[1])

            p02 = ((self.a/2+self.b)/sqrt(2), (-self.a/2-self.b)/sqrt(2))
            p04 = ((-self.a/2-self.b)/sqrt(2), (self.a/2+self.b)/sqrt(2))
        elif self.x_coupler_variant == "+":
            p11 = (0., -height/2.)
            p12 = (0., -height/3.)
            p13 = (0., -height/4.)

            p21 = (length/2., 0.)
            p22 = (length/3., 0.)
            p23 = (length/4., 0.)

            p31 = (0.,-p11[1])
            p32 = (0.,-p12[1])
            p33 = (0.,-p13[1])

            p41 = (-p21[0],0.)
            p42 = (-p22[0],0.)
            p43 = (-p23[0],0.)

            p02 = (self.a/2+self.b, 0.)
            p04 = (-self.a/2-self.b, 0.)

        self.refpoints['p11'] = pya.DPoint(*p11)
        self.refpoints['p21'] = pya.DPoint(*p21)
        self.refpoints['p31'] = pya.DPoint(*p31)
        self.refpoints['p41'] = pya.DPoint(*p41)

        def _add_capacitor_node(p):
            return Node(p, FingerCapacitorSquare,
                    finger_number=self.finger_number,
                    finger_width=self.finger_width,
                    finger_gap_end=self.finger_gap_end,
                    finger_gap=self.finger_gap,
                    a2=self.a,
                    b2=self.b,
                    a=self.a,
                    b=self.b,
                    ground_padding=self.b)

        splitter_port_length = self.a/2 + self.b

        nodes1 = [Node(p11),
                  Node(p12),
                  _add_capacitor_node(p13),
                  Node(p0, WaveguideCoplanarSplitter,
                        angles=[0, 180, 90, 270],
                        lengths=4*[splitter_port_length],
                        a=self.a,
                        b=self.b),
                  _add_capacitor_node(p33),
                  Node(p32),
                  Node(p31)]
        nodes2 = [Node(p41),
                  Node(p42),
                  _add_capacitor_node(p43),
                  Node(p04)]
        nodes3 = [Node(p21),
                  Node(p22),
                  _add_capacitor_node(p23),
                  Node(p02)]

        if self.remove_capacitors:
            nodes1.pop(4)
            nodes1.pop(2)
            nodes2.pop(2)
            nodes3.pop(2)

        if self.x_coupler_variant == 'x' and length == height:
            nodes1.pop(1)
            nodes1.pop(-1)
            nodes2.pop(1)
            nodes3.pop(1)

        self.insert_cell(WaveguideComposite, nodes=nodes1)
        self.insert_cell(WaveguideComposite, nodes=nodes2)
        self.insert_cell(WaveguideComposite, nodes=nodes3)

    @classmethod
    def get_sim_ports(cls, simulation):
        return [RefpointToEdgePort('p11'),
                RefpointToEdgePort('p21'),
                RefpointToEdgePort('p31'),
                RefpointToEdgePort('p41')]
