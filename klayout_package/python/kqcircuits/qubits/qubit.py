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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


from kqcircuits.util.geometry_helper import get_angle
from kqcircuits.elements.element import Element
from kqcircuits.elements.fluxlines.fluxline import Fluxline
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.junctions.squid import Squid
from kqcircuits.junctions.sim import Sim


@add_parameters_from(Fluxline, "fluxline_type")
@add_parameters_from(Squid, "junction_width", "loop_area", "junction_type")
@add_parameters_from(
    Sim,
    "junction_total_length",
    "junction_upper_pad_width",
    "junction_upper_pad_length",
    "junction_lower_pad_width",
    "junction_lower_pad_length",
    "include_background_gap",
)
class Qubit(Element):
    """Base class for qubit objects without actual produce function.

    Collection of shared sub routines for shared parameters and producing shared aspects of qubit geometry including

    * possible fluxlines
    * e-beam layers for SQUIDs
    * SQUID name parameter

    It is customary to also define probepoints for a qubit. Simply define two refpoints as appropriate probepoints.
    For single island qubits::

        self.refpoints["probe_ground"] = pya.DPoint(...)
        self.refpoints["probe_island"] = pya.DPoint(...)
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(
            pya.DBox(-20.0, -20.0, 20.0, 20.0).moved(self.refpoints["probe_ground"]))

    For double island qubits::

        self.refpoints["probe_island_1"] = pya.DPoint(...)
        self.refpoints["probe_island_2"] = pya.DPoint(...)
    """

    LIBRARY_NAME = "Qubit Library"
    LIBRARY_DESCRIPTION = "Library for qubits."
    LIBRARY_PATH = "qubits"

    mirror_squid = Param(pdt.TypeBoolean, "Mirror SQUID by its Y axis", False)

    def produce_squid(self, transf, only_arms=False, **parameters):
        """Produces the squid.

        Creates the squid cell and inserts it with the given transformation as a subcell. Also inserts the squid parts
        in "base_metal_gap_wo_grid"-layer to "base_metal_gap_for_EBL"-layer. It also returns a ``right_side`` refpoint,
        calculated from base_metal_gap_wo_grid layer's bounding box to help with arm_length calculation in
        JunctionTestPads.

        Args:
            transf (DCplxTrans): squid transformation
            parameters: other parameters for the squid
            only_arms: Boolean argument that allows to choose whether to create the arms and the squid device or only
                       the arms

        Returns:
            (dict): Relative refpoints for the squid

        """
        if "junction_type" not in parameters:
            parameters["junction_type"] = self.junction_type
        cell = self.add_element(Squid, **parameters)
        refpoints_rel = self.get_refpoints(cell)
        mwidth = cell.dbbox_per_layer(self.get_layer("base_metal_gap_wo_grid")).width()
        if mwidth > 0.0:
            refpoints_rel["right_side"] = pya.DPoint(mwidth / 2, 0.0)
        squid_transf = transf * pya.DTrans.M90 if self.mirror_squid else transf

        if "squid_index" in parameters:
            s_index = int(parameters.pop("squid_index"))
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

    def produce_fluxline(self, rot=0, displacement=pya.DVector(), **parameters):
        """Produces the fluxline.

        Creates the fluxline cell and inserts it as a subcell. The "flux" and "flux_corner" ports
        are made available for the qubit. By default, fluxlines align their "origin_fluxline" refpoint to
        "origin_squid" refpoint in the direction of "port_common". However, the user might tweak the alignment direction
        by using the argument rot and the relative position by an extra pya.DVector(x, y) allowing to tune the position
        to achieve the desired design parameters.

        Args:
            rot: Extra rotation of the fluxline, in degrees
            displacement (DVector): fluxline x/y displacement (ignored if center alignment is available)
            parameters: parameters for the fluxline to overwrite default and subclass parameters
        """

        if self.fluxline_type == "none":
            return

        cell = self.add_element(Fluxline, **parameters)

        refpoints_so_far = self.get_refpoints(self.cell)
        squid_edge = refpoints_so_far["origin_squid"]
        rotation = get_angle(squid_edge - refpoints_so_far["port_common"]) + 90

        refpoints_fluxline = self.get_refpoints(cell)
        if "center_fluxline" in refpoints_fluxline and "center_squid" in refpoints_so_far:
            total_transformation = pya.DCplxTrans(
                1, rotation + rot, False, refpoints_so_far["center_squid"] - self.refpoints["base"]
            ) * pya.DTrans(-refpoints_fluxline["center_fluxline"])
        else:
            total_transformation = pya.DCplxTrans(
                1, rotation + rot, False, squid_edge - self.refpoints["base"] + displacement
            )

        cell_inst, _ = self.insert_cell(cell, total_transformation)
        self.copy_port("flux", cell_inst)
