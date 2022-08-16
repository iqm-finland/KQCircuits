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

from kqcircuits.util.parameters import Param, pdt
from kqcircuits.qubits.qubit import Qubit
from kqcircuits.pya_resolver import pya


class Swissmon(Qubit):
    """The PCell declaration for a Swissmon qubit.

    Swissmon type qubit. Each arm (West, North, East, South) has it's own arm gap width
    (``gap_width``) and arm metal width (``arm_width``). SQUID is loaded from another library.
    Option of having fluxline.  Refpoints for 3 couplers, fluxline position and chargeline position.
    Length between the ports is from waveguide port to the rectangular part of the launcher pad.
    Length of the fingers is also used for the length of the launcher pad.

    .. MARKERS_FOR_PNG 56,-61 140,0 0,175 -64,117
    """

    arm_length = Param(pdt.TypeList, "Arm length (um, WNES))", [300. / 2] * 4)
    arm_width = Param(pdt.TypeList, "Arm metal width (um, WNES)", [24, 24, 24, 24])
    gap_width = Param(pdt.TypeList, "Arm gap width (um, WNES)", [12, 12, 12, 12])
    cpl_width = Param(pdt.TypeList, "Coupler width (um, WNE)", [24, 24, 24])
    cpl_length = Param(pdt.TypeList, "Coupler lengths (um, WNE)", [120, 120, 120])
    cpl_gap = Param(pdt.TypeList, "Coupler gap (um, WNE)", [102, 102, 102])
    port_width = Param(pdt.TypeList, "Port width (um, WNE)", [10, 10, 10])
    cl_offset = Param(pdt.TypeList, "Chargeline offset (um, um)", [200, 200])
    island_r = Param(pdt.TypeDouble, "Center island rounding radius", 5, unit="μm")

    def build(self):
        self._produce_cross_and_squid()

        self._produce_chargeline()  # refpoint only ATM

        self.produce_fluxline()

        for i in range(3):
            self._produce_coupler(i)

    def _produce_chargeline(self):
        # shorthands
        l = [float(offset) for offset in self.cl_offset]  # swissmon arm length from the center of the cross (refpoint)

        # add ref point
        # port_ref = pya.DPoint(-g-b-a/2, -l)
        port_ref = pya.DPoint(-l[0], -l[1])
        self.add_port("drive", port_ref)

    def _produce_coupler(self, cpl_nr):
        # shorthand
        a = float(self.port_width[cpl_nr])
        b = self.b
        [ww, wn, we, ws] = [float(width) / 2 for width in self.arm_width]
        aw = [ww, wn, we, ws][cpl_nr]
        w = float(self.cpl_width[cpl_nr])
        l = float(self.cpl_length[cpl_nr])
        g = float(self.cpl_gap[cpl_nr]) / 2

        # Location for connecting the waveguides to
        port_shape = pya.DBox(-a / 2, 0, a / 2, b)
        port_region = pya.Region([port_shape.to_itype(self.layout.dbu)])

        if l > 0:
            # Horseshoe opened to below
            # Refpoint in the top center
            shoe_points = [
                pya.DPoint(a, 0),
                pya.DPoint(g + w, 0),
                pya.DPoint(g + w, -l),
                pya.DPoint(g, -l),
                pya.DPoint(g, -w),
                pya.DPoint(-g, -w),
                pya.DPoint(-g, -l),
                pya.DPoint(-g - w, -l),
                pya.DPoint(-g - w, 0),
                pya.DPoint(-a, 0)
            ]
            shoe = pya.DPolygon(shoe_points)
            shoe.size(b)
            shoe.insert_hole(shoe_points[::-1])

            # convert to range and recover CPW port
            shoe_region = pya.Region([shoe.to_itype(self.layout.dbu)])
            shoe_region.round_corners(self.island_r / self.layout.dbu, self.island_r / self.layout.dbu, self.n)
            shoe_region2 = shoe_region - port_region

        # move to the north arm of swiss cross
        ground_width = (2 * g - float(self.gap_width[1]) - 2 * b) / 2
        shift_up = float(self.arm_length[cpl_nr]) + (float(self.gap_width[1]) - 2 * aw) / 2 + ground_width + w + b
        transf = pya.DCplxTrans(1, 0, False, pya.DVector(0, shift_up))

        # rotate to the correct direction
        rotation = [
            pya.DCplxTrans.R90, pya.DCplxTrans.R0, pya.DCplxTrans.R270
        ][cpl_nr]

        # draw
        if l > 0:
            self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(
                shoe_region2.transformed((rotation * transf).to_itrans(self.layout.dbu)))
        self.cell.shapes(self.get_layer("waveguide_path")).insert(
            port_region.transformed((rotation * transf).to_itrans(self.layout.dbu)))

        # protection
        if l > 0:
            protection = pya.DBox(-g - w - b - self.margin, -l - b - self.margin, g + w + b + self.margin,
                                  b + self.margin)
            self.cell.shapes(self.get_layer("ground_grid_avoidance")).\
                insert(protection.transformed((rotation * transf)))

        # add ref point
        port_ref = pya.DPoint(0, b)
        self.add_port("cplr{}".format(cpl_nr), (rotation * transf).trans(port_ref), rotation*pya.DVector(0, 1))

    def _produce_cross_and_squid(self):
        """Produces the cross and squid for the Swissmon."""
        # shorthand
        [ww, wn, we, ws] = [float(width) / 2 for width in self.arm_width]
        l = [float(length) for length in self.arm_length]

        [sw, sn, se, ss] = [float(width) for width in self.gap_width]

        # # SQUID
        # SQUID origin at the ground plane edge
        squid_transf = pya.DCplxTrans(1, 0, False, pya.DVector(0, -l[3] - ss))
        squid_ref_rel = self.produce_squid(squid_transf)
        # SQUID port_common at the end of the south arm
        squid_length = squid_ref_rel["port_common"].distance(pya.DPoint(0, 0))

        # Swissmon etch region

        # refpoint in the center of the swiss cross
        cross_island_points = [
            pya.DPoint(wn, we),
            pya.DPoint(l[2], we),
            pya.DPoint(l[2], -we),
            pya.DPoint(ws, -we),
            pya.DPoint(ws, -l[3] - ss + squid_length),
            pya.DPoint(-ws, -l[3] - ss + squid_length),
            pya.DPoint(-ws, -ww),
            pya.DPoint(-l[0], -ww),
            pya.DPoint(-l[0], ww),
            pya.DPoint(-wn, ww),
            pya.DPoint(-wn, l[1]),
            pya.DPoint(wn, l[1]),
        ]

        # refpoint in the center of the swiss cross
        cross_gap_points = [
            pya.DPoint(wn + sn, we + se),
            pya.DPoint(l[2] + se, we + se),
            pya.DPoint(l[2] + se, -we - se),
            pya.DPoint(ws + ss, -we - se),
            pya.DPoint(ws + ss, -l[3] - ss),
            pya.DPoint(-ws - ss, -l[3] - ss),
            pya.DPoint(-ws - ss, -ww - sw),
            pya.DPoint(-l[0] - sw, -ww - sw),
            pya.DPoint(-l[0] - sw, ww + sw),
            pya.DPoint(-wn - sn, ww + sw),
            pya.DPoint(-wn - sn, l[1] + sn),
            pya.DPoint(wn + sn, l[1] + sn),
        ]

        cross = pya.DPolygon(cross_gap_points)
        cross.insert_hole(cross_island_points)
        cross_rounded = cross.round_corners(self.island_r, self.island_r, self.n)
        region_etch = pya.Region([cross_rounded.to_itype(self.layout.dbu)])
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(region_etch)

        # Protection
        cross_protection = pya.DPolygon([
            p + pya.DVector(math.copysign(max([sw, sn, se, ss]) + self.margin, p.x),
            math.copysign(max([sw, sn, se, ss]) + self.margin, p.y)) for p in cross_gap_points
        ])
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(cross_protection)

        # Probepoint
        probepoint = pya.DPoint(0, 0)
        self.refpoints["probe_qb_c"] = probepoint
