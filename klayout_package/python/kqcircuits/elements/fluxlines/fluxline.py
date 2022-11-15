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


from autologging import logged

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.elements.element import Element
from kqcircuits.defaults import default_fluxline_type
from kqcircuits.elements.fluxlines import fluxline_type_choices


@logged
class Fluxline(Element):
    """Base class for fluxline objects without actual produce function."""

    default_type = default_fluxline_type

    fluxline_type = Param(pdt.TypeString, "Fluxline Type", default_type, choices=fluxline_type_choices)
    fluxline_width = Param(pdt.TypeDouble, "Fluxline width", 18, unit="μm")
    fluxline_gap_width = Param(pdt.TypeDouble, "Fluxline gap width", 2, unit="μm")

    fluxline_parameters = Param(pdt.TypeString, "Extra Fluxline Parameters", "{}")
    _fluxline_parameters = Param(pdt.TypeString, "Previous state of *_parameters", "{}", hidden=True)

    @classmethod
    def create(cls, layout, library=None, fluxline_type=None, **parameters):
        """Create a Fluxline cell in layout."""
        return cls.create_subtype(layout, library, fluxline_type, **parameters)[0]

    def coerce_parameters_impl(self):
        self.sync_parameters(Fluxline)

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
