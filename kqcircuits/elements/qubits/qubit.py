# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.element import Element


class Qubit(Element):
    """ Base class for qubit objects without actual produce function

    Collection of shared sub routines for shared parameters and producing shared aspects of qubit geometry including
    * possible fluxlines
    * e-beam layers for SQUIDs
    * SQUID name parameter

    """

    PARAMETERS_SCHEMA = {
        "corner_r": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Center island rounding radius (um)",
            "default": 5
        },
        "fluxline": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Fluxline",
            "default": True
        },
        "fluxline_variant": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Fluxline variant",
            "default": 1
        },
        "fluxline_gap_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Fluxline gap width for variants 2 and 3 (um)",
            "default": 1
        },
        "squid_name": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "SQUID Type",
            "default": "QCD1"
        },
    }

    def _produce_fluxline(self, variant):
        """ Produce fluxline.

        For relative placement assumes that SQUID is already placed to the cell.

            Arg:
            variant: variant number, 1 | 2
        """

        if not self.fluxline:
            return

        refpoints_so_far = self.get_refpoints(self.cell)
        squid_edge = refpoints_so_far["origin_squid"]
        base = self.refpoints["base"] # superclass has not yet implemented this point
        transf = pya.DTrans(squid_edge-base)

        if variant == 1:
            self._produce_fluxline_variant_1(transf)
        elif variant == 2:
            self._produce_fluxline_variant_2(transf)

    def _produce_fluxline_variant_1(self, transf, width = 18):
        """ Produces a fluxline variant 1.

            Arg:
            transf: transformation of fluxline structure to the SQUID edge.
            width: width of the horizontal segment in um

        """
        # shorthands
        a = self.a  # waveguide center width
        b = self.b  # waveguide gap width
        self.fluxline_width = 10. / 3
        fa = self.fluxline_width  # fluxline center width
        fb = fa * (b / a)  # fluxline gap width
        w = width
        l1 = 30  # straight down
        l2 = 50  # tapering to waveguide port

        # refpoint edge of the cross gap below the arm
        right_gap = pya.DPolygon([
            pya.DPoint(-w / 2 - fa / 2, -fa),
            pya.DPoint(w / 2 + fa / 2 + fb, -fa),
            pya.DPoint(w / 2 + fa / 2 + fb, -fa - l1),
            pya.DPoint(a / 2 + b, -fa - l1 - l2),
            pya.DPoint(a / 2, -fa - l1 - l2),
            pya.DPoint(w / 2 + fa / 2, -fa - l1),
            pya.DPoint(w / 2 + fa / 2, -fa - fb),
            pya.DPoint(-w / 2 - fa / 2, -fa - fb)
        ])
        left_gap = pya.DPolygon([
            pya.DPoint(-w / 2 - fa / 2, -2 * fa - fb),
            pya.DPoint(w / 2 - fa / 2, -2 * fa - fb),
            pya.DPoint(w / 2 - fa / 2, -fa - l1),
            pya.DPoint(-a / 2, -fa - l1 - l2),
            pya.DPoint(-a / 2 - b, -fa - l1 - l2),
            pya.DPoint(w / 2 - fa / 2 - fb, -fa - l1),
            pya.DPoint(w / 2 - fa / 2 - fb, -2 * fa - 2 * fb),
            pya.DPoint(-w / 2 - fa / 2, -2 * fa - 2 * fb)
        ])

        self.cell.shapes(self.layout.layer(self.face()["base metal gap wo grid"])).insert(right_gap.transformed(transf))
        self.cell.shapes(self.layout.layer(self.face()["base metal gap wo grid"])).insert(left_gap.transformed(transf))

        # protection
        protection = pya.Region([p.to_itype(self.layout.dbu) for p in [right_gap, left_gap]]
                                ).bbox().enlarged(self.margin/self.layout.dbu, self.margin/self.layout.dbu)
        self.cell.shapes(self.layout.layer(self.face()["ground grid avoidance"])).insert(protection.transformed(transf.to_itype(self.layout.dbu)))

        # add ref point
        port_ref = pya.DPoint(0, -fa - l1 - l2)
        self.refpoints["port_flux"] = transf.trans(port_ref)
        self.refpoints["port_flux_corner"] = transf.trans(port_ref-pya.DVector(0, self.r))

    def _produce_fluxline_variant_2(self, transf):

        b = self.fluxline_gap_width
        a = (self.a/self.b)*b  # fluxline center width
        l1 = 2*b  # straight down
        bottom_y = -b - l1

        # origin at edge of the cross gap below the arm
        # Right gap of the fluxline. Points created clockwise starting from top left point.
        x_offset = 0  # a + b
        right_gap_pts = [
            pya.DPoint(-b / 2 + x_offset, -b),
            pya.DPoint(b / 2 + x_offset, -b),
            pya.DPoint(b / 2 + x_offset, bottom_y),
            pya.DPoint(-b / 2 + x_offset, bottom_y),
        ]
        right_gap = pya.DPolygon(right_gap_pts)
        # Left gap of the fluxline. Points created clockwise starting from top left point.
        left_gap_pts = [
            right_gap_pts[0] + pya.DPoint(-a - b, 0),
            right_gap_pts[1] + pya.DPoint(-a - b, 0),
            right_gap_pts[2] + pya.DPoint(-a - b, 0),
            right_gap_pts[3] + pya.DPoint(-a - b, 0),
        ]
        left_gap = pya.DPolygon(left_gap_pts)

        # transfer to swiss cross coordinates
        self.cell.shapes(self.layout.layer(self.face()["base metal gap wo grid"])).insert(right_gap.transformed(transf))
        self.cell.shapes(self.layout.layer(self.face()["base metal gap wo grid"])).insert(left_gap.transformed(transf))
        
        # protection
        protection = pya.DBox(
            pya.DPoint(b / 2 + x_offset + self.margin, 0),
            pya.DPoint(-b / 2 + x_offset -a - b - self.margin, bottom_y),
        )
        self.cell.shapes(self.layout.layer(self.face()["ground grid avoidance"])).insert(protection.transformed(transf))

        # add ref point
        port_ref = pya.DPoint(-a/2 - b/2 + x_offset, bottom_y)
        self.refpoints["port_flux"] = transf.trans(port_ref)
        self.refpoints["port_flux_corner"] = transf.trans(port_ref-pya.DVector(0, self.r))