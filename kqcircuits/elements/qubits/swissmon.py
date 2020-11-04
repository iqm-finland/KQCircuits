# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import math
from autologging import traced

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.element import Element
from kqcircuits.elements.qubits.qubit import Qubit


@traced
class Swissmon(Qubit):
    """The PCell declaration for a Swissmon qubit.

    Swissmon type qubit. Each arm (West, North, East, South) has it’s own width. “Hole” for the island has the same
    gap_width for each arm. SQUID is loaded from another library. Option of having fluxline. Refpoints for 3
    couplers, fluxline position and chargeline position.
    """

    PARAMETERS_SCHEMA = {
        "arm_length": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Arm length (um, WNES))",
            "default": [300. / 2] * 4
        },
        "arm_width": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Arm width (um, WNES)",
            "default": [24, 24, 24, 24]
        },
        "gap_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Arm gap full width [μm]",
            "default": 48
        },
        "cpl_width": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Coupler width (um, WNE)",
            "default": [24, 24, 24]
        },
        "cpl_length": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Coupler lengths (um, WNE)",
            "default": [160, 160, 160]
        },
        "cpl_gap": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Coupler gap (um, WNE)",
            "default": [102, 102, 102]
        },
        "port_width": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Port width (um, WNE)",
            "default": [10, 10, 10]
        },
        "cl_offset": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Chargeline offset (um, um)",
            "default": [200, 200]
        }
    }

    def produce_impl(self):
        self._produce_cross_and_squid()

        self._produce_chargeline()  # refpoint only ATM

        self._produce_fluxline(self.fluxline_variant)

        for i in range(3):
            self._produce_coupler(i)

        # adds annotation based on refpoints calculated above
        super().produce_impl()

    def _produce_chargeline(self):
        # shorthands
        g = self.gap_width  # gap width
        [we, wn, ww, ws] = [float(width) / 2 for width in self.arm_width]  # length of the horizontal segment
        w = wn  # length of the horizontal segment
        l = [float(offset) for offset in self.cl_offset]  # swissmon arm length from the center of the cross (refpoint)
        a = self.a  # cpw center conductor width
        b = self.b  # cpw gap width

        # add ref point
        # port_ref = pya.DPoint(-g-b-a/2, -l)
        port_ref = pya.DPoint(-l[0], -l[1])
        self.add_port("drive", port_ref)

    def _produce_coupler(self, cpl_nr):
        # shorthand
        a = float(self.port_width[cpl_nr])
        b = self.b
        [we, wn, ww, ws] = [float(width) / 2 for width in self.arm_width]
        aw = [we, wn, ww, ws][cpl_nr]
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
            shoe_region.round_corners(self.corner_r / self.layout.dbu, self.corner_r / self.layout.dbu, self.n)
            shoe_region2 = shoe_region - port_region

        # move to the north arm of swiss cross
        ground_width = (2 * g - self.gap_width - 2 * b) / 2
        shift_up = float(self.arm_length[cpl_nr]) + (self.gap_width - 2 * aw) / 2 + ground_width + w + b
        transf = pya.DCplxTrans(1, 0, False, pya.DVector(0, shift_up))

        # rotate to the correct direction
        rotation = [
            pya.DCplxTrans.R90, pya.DCplxTrans.R0, pya.DCplxTrans.R270
        ][cpl_nr]

        # draw
        if l > 0:
            self.cell.shapes(self.get_layer("base metal gap wo grid")).insert(
                shoe_region2.transformed((rotation * transf).to_itrans(self.layout.dbu)))
        self.cell.shapes(self.get_layer("annotations")).insert(
            port_region.transformed((rotation * transf).to_itrans(self.layout.dbu)))

        # protection
        if l > 0:
            protection = pya.DBox(-g - w - b - self.margin, -l - b - self.margin, g + w + b + self.margin,
                                  b + self.margin)
            self.cell.shapes(self.get_layer("ground grid avoidance")).insert(protection.transformed((rotation * transf)))

        # add ref point
        port_ref = pya.DPoint(0, b)
        self.add_port("cplr{}".format(cpl_nr), (rotation * transf).trans(port_ref), rotation*pya.DVector(0, 1))

    def _produce_cross_and_squid(self):
        """Produces the cross and squid for the Swissmon."""
        # shorthand
        [we, wn, ww, ws] = [float(width) / 2 for width in self.arm_width]
        l = [float(length) for length in self.arm_length]

        s = self.gap_width / 2

        # SQUID
        squid_cell = Element.create_cell_from_shape(self.layout, self.squid_name)
        squid_pos_rel = self.get_refpoints(squid_cell)
        # SQUID port_common at the end of the south arm
        squid_length = squid_pos_rel["port_common"].distance(pya.DPoint(0, 0))

        # SQUID origin at the ground plane edge
        squid_transf = pya.DCplxTrans(1, 0, False, pya.DVector(0, -l[3] - (s - ws)))
        squid_unetch_region = self.produce_squid(squid_cell, squid_transf)

        # Swissmon etch region

        # refpoint in the center of the swiss cross
        cross_island_points = [
            pya.DPoint(wn, ww),
            pya.DPoint(l[2], ww),
            pya.DPoint(l[2], -ww),
            pya.DPoint(ws, -ww),
            pya.DPoint(ws, -l[3] - (s - we) + squid_length),
            pya.DPoint(-ws, -l[3] - (s - we) + squid_length),
            pya.DPoint(-ws, -we),
            pya.DPoint(-l[0], -we),
            pya.DPoint(-l[0], we),
            pya.DPoint(-wn, we),
            pya.DPoint(-wn, l[1]),
            pya.DPoint(wn, l[1]),
        ]

        # refpoint in the center of the swiss cross
        cross_gap_points = [
            pya.DPoint(s, s),
            pya.DPoint(l[2] + (s - ww), s),
            pya.DPoint(l[2] + (s - ww), -s),
            pya.DPoint(s, -s),
            pya.DPoint(s, -l[3] - (s - ws)),
            pya.DPoint(-s, -l[3] - (s - ws)),
            pya.DPoint(-s, -s),
            pya.DPoint(-l[0] - (s - we), -s),
            pya.DPoint(-l[0] - (s - we), s),
            pya.DPoint(-s, s),
            pya.DPoint(-s, l[1] + (s - wn)),
            pya.DPoint(s, l[1] + (s - wn)),
        ]

        cross = pya.DPolygon(cross_gap_points)
        cross.insert_hole(cross_island_points)
        cross_rounded = cross.round_corners(self.corner_r, self.corner_r, self.n)
        region_etch = pya.Region([cross_rounded.to_itype(self.layout.dbu)]) - squid_unetch_region
        self.cell.shapes(self.get_layer("base metal gap wo grid")).insert(region_etch)

        # Protection
        cross_protection = pya.DPolygon([
            p + pya.DVector(math.copysign(s + self.margin, p.x), math.copysign(s + self.margin, p.y)) for p in
            cross_gap_points
        ])
        self.cell.shapes(self.get_layer("ground grid avoidance")).insert(cross_protection)

        # Probepoint
        probepoint = pya.DPoint(0, 0)
        self.refpoints["probe_qb_c"] = probepoint
