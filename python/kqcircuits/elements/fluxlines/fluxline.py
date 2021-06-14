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
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.util.library_helper import load_libraries, to_library_name
from kqcircuits.elements.element import Element
from kqcircuits.defaults import default_fluxline_type


@traced
@logged
class Fluxline(Element):
    """Base class for fluxline objects without actual produce function."""

    # Parameters defined here will be inherited by Qubit, and are to be common for multiple fluxlines.  Subclasses of
    # Fluxline should override the defaults (of any parameters they use) with a suitable default value for the
    # particular design.The default value here should be a special "unphysical" value, e.g. 0, which indicates that the
    # default of the particular Fluxline subclass should be used.
    fluxline_width = Param(pdt.TypeDouble, "Fluxline width", 0, unit="μm")
    fluxline_gap_width = Param(pdt.TypeDouble, "Fluxline gap width", 0, unit="μm")

    @classmethod
    def create(cls, layout, fluxline_type=None, **parameters):
        """Create a Fluxline cell in layout.

        If fluxline_type is unknown the default is returned.

        Overrides Element.create(), so that functions like add_element() and insert_cell() will call this instead.

        Args:
            layout: pya.Layout object where this cell is created
            fluxline_type (str): name of the Fluxline subclass or manually designed cell
            **parameters: PCell parameters for the element as keyword arguments

        Returns:
            the created fluxline cell
        """

        if fluxline_type is None:
            fluxline_type = to_library_name(cls.__name__)

        library_layout = (load_libraries(path=cls.LIBRARY_PATH)[cls.LIBRARY_NAME]).layout()
        if fluxline_type in library_layout.pcell_names():   #code generated
            pcell_class = type(library_layout.pcell_declaration(fluxline_type))
            return Element._create_cell(pcell_class, layout, **parameters)
        elif library_layout.cell(fluxline_type):    # manually designed
            return layout.create_cell(fluxline_type, cls.LIBRARY_NAME)
        else:   # fallback is the default
            return Fluxline.create(layout, fluxline_type=default_fluxline_type, **parameters)

    def _insert_fluxline_shapes(self, left_gap, right_gap):
        """Inserts the gap shapes to the cell.

        Protection layer is added based on their bounding box.

        Arg:
            left_gap (DPolygon): polygon for the left gap
            right_gap (DPolygon): polygon for the right gap
        """
        # transfer to qubit coordinates
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(left_gap)
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(right_gap)
        # protection
        protection = pya.Region([p.to_itype(self.layout.dbu) for p in [right_gap, left_gap]]
                                ).bbox().enlarged(self.margin/self.layout.dbu, self.margin/self.layout.dbu)
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(pya.Polygon(protection))

    def _add_fluxline_refpoints(self, port_ref):
        """Adds refpoints for "port_flux" and "port_flux_corner".

        Arg:
            port_ref (DPoint): position of "port_flux" in fluxline coordinates
        """
        self.refpoints["origin_fluxline"] = pya.DPoint(0, 0)
        self.add_port("flux", port_ref, pya.DVector(0, -1))
        super().produce_impl()
