# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
import math
from kqcircuits.pya_resolver import pya
from kqcircuits.elements.element import Element
from kqcircuits.elements.airbridge import Airbridge
from kqcircuits.elements.waveguide_coplanar_taper import WaveguideCoplanarTaper


class Qubit(Element):
    """Base class for qubit objects without actual produce function.

    Collection of shared sub routines for shared parameters and producing shared aspects of qubit geometry including

    * possible fluxlines
    * e-beam layers for SQUIDs
    * SQUID name parameter

    """

    PARAMETERS_SCHEMA = {
        "corner_r": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Center island rounding radius [μm]",
            "default": 5
        },
        "squid_name": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "SQUID Type",
            "default": "QCD1"
        },
        "fluxline_variant": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Fluxline variant",
            "default": "standard",
            "choices": [["None", "none"],
                        ["Standard (1)", "standard"],
                        ["Straight vertical (2)", "straight vertical"],
                        ["Cut-ground (3)", "cut-ground"]]
        },
        "fluxline_gap_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Fluxline gap width for variants 2 and 3 [μm]",
            "default": 3
        },
        "fluxline_h_length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Horizontal fluxline length (variant 3) [μm]",
            "docstring": "Fluxline horizontal part length for variant 3 [μm]",
            "default": 21
        },
        "fluxline_offset": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Fluxline offset for variant 3 (um, um)",
            "default": [-13.5, 0]
        },
        "junction_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Junction width for code generated squids",
            "docstring": "Junction width (only used for code generated squids)",
            "default": 0.02
        },
    }

    def produce_squid(self, cell, transf):
        """Produces the squid.

        Inserts the squid cell with the given transformation as a subcell, and finds the unetch region for this
        squid. Also inserts the squid parts in "base metal gap wo grid"-layer to "base metal gap for EBL"-layer.

        Args:
            cell (Cell): squid cell
            transf (DCplxTrans): squid transformation

        Returns:
            squid unetch region (Region)
        """

        # For the region transformation, we need to use ICplxTrans, which causes some rounding errors. For inserting
        # the cell, convert the integer transform back to float to keep cell and geometry consistent
        integer_transf = transf.to_itrans(self.layout.dbu)
        float_transf = integer_transf.to_itrans(self.layout.dbu)  # Note: ICplxTrans.to_itrans returns DCplxTrans

        self.insert_cell(cell, float_transf)
        squid_unetch_region = pya.Region(cell.shapes(self.get_layer("base metal addition")))
        squid_unetch_region.transform(integer_transf)
        # add parts of qubit to the layer needed for EBL
        squid_etch_region = pya.Region(cell.shapes(self.get_layer("base metal gap wo grid")))
        squid_etch_region.transform(integer_transf)
        self.cell.shapes(self.get_layer("base metal gap for EBL")).insert(squid_etch_region)
        return squid_unetch_region

    def _produce_fluxline(self, variant):
        """Produce fluxline.

        For relative placement assumes that SQUID is already placed to the cell.

        Args:
            variant: variant name, "standard" | "straight vertical" | "cut-ground"
        """

        if variant == "none":
            return

        refpoints_so_far = self.get_refpoints(self.cell)
        squid_edge = refpoints_so_far["origin_squid"]
        base = self.refpoints["base"]  # superclass has not yet implemented this point
        a = (squid_edge - refpoints_so_far['port_common'])
        rotation = math.atan2(a.y, a.x) / math.pi * 180 + 90
        transf = pya.DCplxTrans(1, rotation, False, squid_edge-base)

        if variant == "standard":
            self._produce_fluxline_standard(transf)
        elif variant == "straight vertical":
            self._produce_fluxline_straight_vertical(transf)
        elif variant == "cut-ground":
            self._produce_fluxline_cut_ground(transf)

    def _produce_fluxline_standard(self, transf, width=18):
        """Produces a fluxline variant "standard".

        Args:
            transf: transformation of fluxline structure to the SQUID edge.
            width: width of the horizontal segment

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

        # origin at edge of the qubit gap
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

        self._insert_fluxline_shapes(left_gap, right_gap, transf)
        self._add_fluxline_refpoints(pya.DPoint(0, -fa - l1 - l2), transf)

    def _produce_fluxline_straight_vertical(self, transf):
        """Produces a fluxline variant "straight vertical".

        Arg:
            transf: transformation of fluxline structure to the SQUID edge.
        """

        b = self.fluxline_gap_width
        a = (self.a/self.b)*b  # fluxline center width
        l1 = 2*b  # straight down
        bottom_y = -b - l1

        # origin at edge of the qubit gap

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

        self._insert_fluxline_shapes(left_gap, right_gap, transf)
        self._add_fluxline_refpoints(pya.DPoint(-a/2 - b/2 + x_offset, bottom_y), transf)

    def _produce_fluxline_cut_ground(self, transf):
        """Produces a fluxline variant "cut-ground".

        By default, the end of fluxline center conductor vertical part is horizontally centered w.r.t. squid origin and
        vertically displaced from it by "fluxline_gap_width". This location can be adjusted using "fluxline_offset"
        parameter.

        Arg:
            transf: transformation of fluxline structure to the SQUID edge.
        """
        b = self.fluxline_gap_width
        a = (self.a/self.b)*b  # fluxline center width
        offset = pya.DVector(float(self.fluxline_offset[0]), float(self.fluxline_offset[1]))
        bottom_y = -3*b + offset.y

        # origin at edge of the qubit gap

        # Left gap of the fluxline. Points created clockwise starting from top left point.
        left_gap_pts = [
            pya.DPoint(offset.x - a/2 - b, 0),
            pya.DPoint(offset.x - a/2, 0),
            pya.DPoint(offset.x - a/2, bottom_y),
            pya.DPoint(offset.x - a/2 - b, bottom_y),
        ]
        left_gap = pya.DPolygon(left_gap_pts)

        # Right gap of the fluxline. Points created clockwise starting from top left point.
        right_gap_pts = [
            left_gap_pts[0] + pya.DPoint(a + b, -b + offset.y),
            left_gap_pts[1] + pya.DPoint(a + b + self.fluxline_h_length, -b + offset.y),
            left_gap_pts[1] + pya.DPoint(a + b + self.fluxline_h_length, -2*b + offset.y),
            left_gap_pts[1] + pya.DPoint(a + b, -2*b + offset.y),
            left_gap_pts[2] + pya.DPoint(a + b, 0),
            left_gap_pts[3] + pya.DPoint(a + b, 0),
        ]
        right_gap = pya.DPolygon(right_gap_pts)

        # add taper to normal waveguide "a" and "b"
        taper_length = 80
        taper_cell = self.add_element(WaveguideCoplanarTaper,
            taper_length=taper_length,
            a1=a,
            b1=b,
            m1=self.margin,
            a2=self.a,
            b2=self.b,
            m2=self.margin
        )
        taper_pos = pya.DPoint(offset.x, bottom_y)
        self.insert_cell(taper_cell, transf*pya.DTrans(3, False, taper_pos))

        self._insert_fluxline_shapes(left_gap, right_gap, transf)
        self._add_fluxline_refpoints(taper_pos + pya.DVector(0, -taper_length), transf)

        ab = self.add_element(Airbridge)
        self.insert_cell(ab, trans=pya.DCplxTrans(1, 90+transf.angle, False,
                                                  self.refpoints["port_flux"]-self.refpoints["base"]))

    def _insert_fluxline_shapes(self, left_gap, right_gap, transf):
        """Inserts the gap shapes to the cell.

        The shapes are transformed by "transf". Protection layer is added based on their bounding box.

        Arg:
            left_gap (DPolygon): polygon for the left gap
            right_gap (DPolygon): polygon for the right gap
            transf: transformation of fluxline structure to the SQUID edge.
        """
        # transfer to qubit coordinates
        self.cell.shapes(self.get_layer("base metal gap wo grid")).insert(left_gap.transformed(transf))
        self.cell.shapes(self.get_layer("base metal gap wo grid")).insert(right_gap.transformed(transf))
        # protection
        protection = pya.Region([p.to_itype(self.layout.dbu) for p in [right_gap, left_gap]]
                                ).bbox().enlarged(self.margin/self.layout.dbu, self.margin/self.layout.dbu)
        self.cell.shapes(self.get_layer("ground grid avoidance")).insert(
            pya.Polygon(protection).transformed(transf.to_itrans(self.layout.dbu)))

    def _add_fluxline_refpoints(self, port_ref, transf):
        """Adds refpoints for "port_flux" and "port_flux_corner".

        The given point is transformed by "transf" to obtain the refpoints

        Arg:
            port_ref (DPoint): position of "port_flux" in fluxline coordinates
            transf: transformation of fluxline structure to the SQUID edge.
        """
        self.add_port("flux", transf.trans(port_ref), transf.trans(pya.DVector(0, -1)))
