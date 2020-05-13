# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from autologging import logged, traced

from kqcircuits.elements.element import Element


@logged
@traced
class Airbridge(Element):
    """PCell declaration for an airbridge.

    Origin is at the geometric center. The airbridge is in vertical direction. There are two versions of the
    airbridge: normal or bow-tie.

    Bottom parts of pads in bottom layer, bridge and top parts of pads in top layer. Pads and bridge are rectangular.
    Refpoints "port_a" and "port_b" at top pad points closest to origin.

    Attributes:

        bridge_width: Bridge width
        bridge_length: Bridge length from pad tip to pad tip
        pad_width: width of the pads
        pad_length: length of the pads (for bow-tie this doesn't include the taper part)
        pad_extra: added to pad_width and pad_length for bottom pads

    """

    PARAMETERS_SCHEMA = {
        "bridge_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Bridge width (um)",
            "default": 20
        },
        "bridge_length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Bridge length (from pad to pad) (um)",
            "default": 60
        },
        "pad_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Pad width (um)",
            "default": 20
        },
        "pad_length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Pad length (um)",
            "default": 14
        },
        "pad_extra": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Bottom pad extra (um)",
            "default": 2
        },
    }

    def __init__(self):
        super().__init__()

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "Airbridge({})".format(self.name)

    def produce_impl(self):

        self._produce_bottom_pads()
        self._produce_top_pads_and_bridge()

    def _produce_bottom_pads(self, pad_taper_length=0):

        # shorthand
        w = self.pad_width
        h = self.pad_length
        l = self.bridge_length
        e = self.pad_extra

        # bottom layer upper pad
        pts = [
            pya.DPoint(-w / 2 - e, l / 2 - e),
            pya.DPoint(-w / 2 - e, h + l / 2 + e),
            pya.DPoint(w / 2 + e, h + l / 2 + e),
            pya.DPoint(w / 2 + e, l / 2 - e),
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.layout.layer(self.face()["airbridge pads"])).insert(shape)

        # bottom layer lower pad
        self.cell.shapes(self.layout.layer(self.face()["airbridge pads"])).insert(pya.DTrans.M0 * shape)

        # protection layer
        self.cell.shapes(self.layout.layer(self.face()["ground grid avoidance"])).insert(shape.sized(self.margin))
        self.cell.shapes(self.layout.layer(self.face()["ground grid avoidance"])).insert(pya.DTrans.M0 * shape.sized(self.margin))

        # refpoints for connecting to waveguides
        self.refpoints["port_a"] = pya.DPoint(0, l / 2)
        self.refpoints["port_b"] = pya.DPoint(0, -l / 2)
        # adds annotation based on refpoints calculated above
        super().produce_impl()

    def _produce_top_pads_and_bridge(self):

        # shorthand
        w = self.pad_width
        h = self.pad_length
        l = self.bridge_length
        b = self.bridge_width

        # top layer
        pts = [
            pya.DPoint(-w / 2, h + l / 2),
            pya.DPoint(w / 2, h + l / 2),
            pya.DPoint(w / 2, l / 2),
            pya.DPoint(b / 2, l / 2),
            pya.DPoint(b / 2, -l / 2),
            pya.DPoint(w / 2, -l / 2),
            pya.DPoint(w / 2, -h - l / 2),
            pya.DPoint(-w / 2, -h - l / 2),
            pya.DPoint(-w / 2, -l / 2),
            pya.DPoint(-b / 2, -l / 2),
            pya.DPoint(-b / 2, l / 2),
            pya.DPoint(-w / 2, l / 2),
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.layout.layer(self.face()["airbridge flyover"])).insert(shape)
