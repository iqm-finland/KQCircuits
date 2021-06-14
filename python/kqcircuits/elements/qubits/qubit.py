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


import math

from kqcircuits.defaults import default_squid_type, default_fluxline_type
from kqcircuits.elements.element import Element
from kqcircuits.elements.fluxlines import fluxline_type_choices
from kqcircuits.elements.fluxlines.fluxline import Fluxline
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.squids import squid_type_choices
from kqcircuits.squids.squid import Squid


@add_parameters_from(Fluxline)
class Qubit(Element):
    """Base class for qubit objects without actual produce function.

    Collection of shared sub routines for shared parameters and producing shared aspects of qubit geometry including

    * possible fluxlines
    * e-beam layers for SQUIDs
    * SQUID name parameter
    """

    corner_r = Param(pdt.TypeDouble, "Center island rounding radius", 5, unit="μm")
    squid_type = Param(pdt.TypeString, "SQUID Type", default_squid_type, choices=squid_type_choices)
    junction_width = Param(pdt.TypeDouble, "Junction width for code generated squids", 0.02,
        docstring="Junction width (only used for code generated squids)")
    fluxline_type = Param(pdt.TypeString, "Fluxline Type", default_fluxline_type, choices=fluxline_type_choices)

    def produce_squid(self, transf, **parameters):
        """Produces the squid.

        Creates the squid cell and inserts it with the given transformation as a subcell. Also inserts the squid parts
        in "base_metal_gap_wo_grid"-layer to "base_metal_gap_for_EBL"-layer.

        Args:
            transf (DCplxTrans): squid transformation
            parameters: other parameters for the squid

        Returns:
            A tuple ``(squid_unetch_region, refpoints_rel)``

            * ``squid_unetch_region`` (Region):  squid unetch region
            * ``refpoints_rel`` (Dictionary): relative refpoints for the squid

        """
        cell = self.add_element(Squid, squid_type=self.squid_type, junction_width=self.junction_width,
                                margin=self.margin, face_ids=self.face_ids, **parameters)
        refpoints_rel = self.get_refpoints(cell)

        # For the region transformation, we need to use ICplxTrans, which causes some rounding errors. For inserting
        # the cell, convert the integer transform back to float to keep cell and geometry consistent
        integer_transf = transf.to_itrans(self.layout.dbu)
        float_transf = integer_transf.to_itrans(self.layout.dbu)  # Note: ICplxTrans.to_itrans returns DCplxTrans

        self.insert_cell(cell, float_transf)
        squid_unetch_region = pya.Region(cell.shapes(self.get_layer("base_metal_addition")))
        squid_unetch_region.transform(integer_transf)
        # add parts of qubit to the layer needed for EBL
        squid_etch_region = pya.Region(cell.shapes(self.get_layer("base_metal_gap_wo_grid")))
        squid_etch_region.transform(integer_transf)
        self.cell.shapes(self.get_layer("base_metal_gap_for_EBL")).insert(squid_etch_region)

        return squid_unetch_region, refpoints_rel

    def produce_fluxline(self):
        """Produces the fluxline.

        Creates the fluxline cell and inserts it as a subcell. The "flux" and "flux_corner" ports
        are made available for the qubit.
        """

        if self.fluxline_type == "none":
            return

        # Pass only fluxline parameters which differ from the class default value. This allows subclasses to override
        # the default value
        fluxline_parameters = {}
        for key, param in type(self).get_schema().items():
            if key.startswith('fluxline_'):
                value = self.__getattribute__(key)
                if value != param.default:
                    fluxline_parameters[key] = value

        fluxline = self.add_element(
            Fluxline,
            a=self.a,
            b=self.b,
            face_ids=self.face_ids,
            **fluxline_parameters,
        )

        refpoints_so_far = self.get_refpoints(self.cell)
        squid_edge = refpoints_so_far["origin_squid"]
        base = self.refpoints["base"]  # superclass has not yet implemented this point
        a = (squid_edge - refpoints_so_far['port_common'])
        rotation = math.atan2(a.y, a.x) / math.pi * 180 + 90
        transf = pya.DCplxTrans(1, rotation, False, squid_edge-base)

        _, fl_ref = self.insert_cell(fluxline, transf)
        self.add_port("flux", fl_ref["port_flux"], fl_ref["port_flux_corner"] - fl_ref["port_flux"])
