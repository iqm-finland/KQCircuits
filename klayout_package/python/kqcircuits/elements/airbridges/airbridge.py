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
from kqcircuits.util.geometry_helper import get_angle
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.defaults import default_airbridge_type, default_layers
from kqcircuits.elements.airbridges import airbridge_type_choices
from kqcircuits.elements.element import Element, get_refpoints


class Airbridge(Element):
    """Airbridge base class without actual produce function.

    All subclasses should have ports 'a' and 'b' at positions (0, bridge_length) and (0, -bridge_length).
    """

    default_type = default_airbridge_type
    """This is the default shape if not specified otherwise by the user."""

    airbridge_type = Param(pdt.TypeString, "Airbridge type", default_type, choices=airbridge_type_choices)
    bridge_width = Param(pdt.TypeDouble, "Bridge width", 20, unit="μm")
    pad_length = Param(pdt.TypeDouble, "Pad length", 18, unit="μm")
    bridge_length = Param(pdt.TypeDouble, "Bridge length (from pad to pad)", 44, unit="μm")

    @classmethod
    def create(cls, layout, library=None, airbridge_type=None, **parameters):
        """Create cell for an airbridge in layout."""
        cell, code_generated = cls.create_subtype(layout, library, airbridge_type, **parameters)

        # transform cell to have 'port_a' at (0, l/2) and 'port_b' at (0, -l/2), where l is distance between ports
        if not code_generated:
            ref_points = get_refpoints(layout.layer(default_layers["refpoints"]), cell)
            center = (ref_points['port_a'] + ref_points['port_b']) / 2
            orientation = get_angle(ref_points['port_a'] - ref_points['port_b'])
            cell.transform(pya.DCplxTrans(1.0, 90 - orientation, False, -center))

        return cell

    def _produce_bottom_pads(self, pts):
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("airbridge_pads")).insert(shape)

        # bottom layer lower pad
        self.cell.shapes(self.get_layer("airbridge_pads")).insert(pya.DTrans.M0 * shape)

        # protection layer
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(shape.sized(self.margin))
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(pya.DTrans.M0 * shape.sized(self.margin))

        # refpoints for connecting to waveguides
        self.add_port("a", pya.DPoint(0, self.bridge_length / 2), pya.DVector(0, 1))
        self.add_port("b", pya.DPoint(0, -self.bridge_length / 2), pya.DVector(0, -1))

    def _produce_top_pads_and_bridge(self, pts):
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("airbridge_flyover")).insert(shape)
