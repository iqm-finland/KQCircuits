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


from autologging import logged, traced
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import get_angle
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.util.library_helper import load_libraries
from kqcircuits.defaults import default_airbridge_type, default_layers

from kqcircuits.elements.element import Element, get_refpoints


@traced
@logged
class Airbridge(Element):
    """Airbridge base class without actual produce function.

    All subclasses should have ports 'a' and 'b' at positions (0, bridge_length) and (0, -bridge_length).
    """

    default_type = default_airbridge_type
    """This is the default shape if not specified otherwise by the user."""

    bridge_width = Param(pdt.TypeDouble, "Bridge width", 20, unit="μm")
    pad_length = Param(pdt.TypeDouble, "Pad length", 18, unit="μm")
    bridge_length = Param(pdt.TypeDouble, "Bridge length (from pad to pad)", 44, unit="μm")

    @classmethod
    def create(cls, layout, library=None, airbridge_type=None, **parameters):
        """Create cell for an airbridge in layout.

        The cell is created either from a pcell class or a from a manual design file, depending on airbridge_type.
        If airbridge_type is unknown the default is returned.

        Overrides Element.create(), so that functions like add_element() and insert_cell() will call this instead.

        Args:
            layout: pya.Layout object where this cell is created
            library: LIBRARY_NAME of the calling PCell instance
            airbridge_type (str): name of the Airbridge subclass or manually designed cell
            **parameters: PCell parameters for the element as keyword arguments

        Returns:
            the created airbridge cell
        """

        if airbridge_type is None:
            airbridge_type = cls.default_type

        library_layout = (load_libraries(path=cls.LIBRARY_PATH)[cls.LIBRARY_NAME]).layout()
        if airbridge_type in library_layout.pcell_names():     # code generated, create like a normal element
            pcell_class = type(library_layout.pcell_declaration(airbridge_type))
            return Element._create_cell(pcell_class, layout, library, **parameters)
        elif library_layout.cell(airbridge_type):              # manually designed, load from .oas
            cell = layout.create_cell(airbridge_type, cls.LIBRARY_NAME)
            # transform cell to have 'port_a' at (0, l/2) and 'port_b' at (0, -l/2), where l is distance between ports
            ref_points = get_refpoints(layout.layer(default_layers["refpoints"]), cell)
            center = (ref_points['port_a'] + ref_points['port_b']) / 2
            orientation = get_angle(ref_points['port_a'] - ref_points['port_b'])
            cell.transform(pya.DCplxTrans(1.0, 90 - orientation, False, -center))
            return cell
        else:                                               # fallback is the default
            return Airbridge.create(layout, library, airbridge_type=cls.default_type, **parameters)

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
