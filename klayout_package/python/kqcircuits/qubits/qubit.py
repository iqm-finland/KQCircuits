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

from kqcircuits.elements.element import Element
from kqcircuits.elements.fluxlines.fluxline import Fluxline
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.squids.squid import Squid


@add_parameters_from(Fluxline, "fluxline_gap_width", "fluxline_type")
@add_parameters_from(Squid, "junction_width", "loop_area", "squid_type")
class Qubit(Element):
    """Base class for qubit objects without actual produce function.

    Collection of shared sub routines for shared parameters and producing shared aspects of qubit geometry including

    * possible fluxlines
    * e-beam layers for SQUIDs
    * SQUID name parameter
    """

    LIBRARY_NAME = "Qubit Library"
    LIBRARY_DESCRIPTION = "Library for qubits."
    LIBRARY_PATH = "qubits"

    mirror_squid =  Param(pdt.TypeBoolean, "Mirror SQUID by its Y axis", False)

    def produce_squid(self, transf, only_arms=False, **parameters):
        """Produces the squid.

        Creates the squid cell and inserts it with the given transformation as a subcell. Also inserts the squid parts
        in "base_metal_gap_wo_grid"-layer to "base_metal_gap_for_EBL"-layer.

        Args:
            transf (DCplxTrans): squid transformation
            parameters: other parameters for the squid
            only_arms: Boolean argument that allows to choose whether to create the arms and the squid device or only
                       the arms

        Returns:
            (dict): Relative refpoints for the squid

        """
        cell = self.add_element(Squid, squid_type=self.squid_type, **parameters)
        refpoints_rel = self.get_refpoints(cell)
        squid_transf = transf * pya.DTrans.M90 if self.mirror_squid else transf

        if "squid_index" in parameters:
            s_index = int(parameters.pop('squid_index'))
            inst, _ = self.insert_cell(cell, squid_transf, inst_name=f"squid_{s_index}")
            inst.set_property("squid_index", s_index)
        else:
            inst, _ = self.insert_cell(cell, squid_transf, inst_name="squid")

        if only_arms:
            # add squid metal etch and unetch shapes to qubit and erase instance of squid
            for layer_name in ["base_metal_gap_wo_grid", "base_metal_addition"]:
                region = pya.Region(cell.shapes(self.get_layer(layer_name)))
                region.transform(inst.cplx_trans)
                self.cell.shapes(self.get_layer(layer_name)).insert(region)
            self.cell.erase(inst)
        else:
            # add parts of qubit to the layer needed for EBL
            region = pya.Region(cell.shapes(self.get_layer("base_metal_gap_wo_grid")))
            region.transform(inst.cplx_trans)
            self.cell.shapes(self.get_layer("base_metal_gap_for_EBL")).insert(region)

        return refpoints_rel

    def produce_fluxline(self, **parameters):
        """Produces the fluxline.

        Creates the fluxline cell and inserts it as a subcell. The "flux" and "flux_corner" ports
        are made available for the qubit.

        Args:
            parameters: parameters for the fluxline to overwrite default and subclass parameters
        """

        if self.fluxline_type == "none":
            return
        parameters = {"fluxline_type": self.fluxline_type, **parameters}

        cell = self.add_element(Fluxline, **parameters)

        refpoints_so_far = self.get_refpoints(self.cell)
        squid_edge = refpoints_so_far["origin_squid"]
        a = (squid_edge - refpoints_so_far['port_common'])
        rotation = math.atan2(a.y, a.x) / math.pi * 180 + 90
        transf = pya.DCplxTrans(1, rotation, False, squid_edge - self.refpoints["base"])

        cell_inst, _ = self.insert_cell(cell, transf)
        self.copy_port("flux", cell_inst)
