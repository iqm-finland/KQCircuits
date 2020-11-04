# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from autologging import logged, traced

from kqcircuits.elements.element import Element


@traced
@logged
class Airbridge(Element):
    """PCell declaration for an airbridge.

    Origin is at the geometric center. The airbridge is in vertical direction. There are different versions of the
    airbridge: normal.

    normal:
    Bottom parts of pads in bottom layer, bridge and top parts of pads in top layer. Pads and bridge are rectangular.
    Refpoints "port_a" and "port_b" at top pad points closest to origin.

    """

    PARAMETERS_SCHEMA = {
        "bridge_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Bridge width [μm]",
            "default": 20
        },
        "bridge_length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Bridge length (from pad to pad) [μm]",
            "default": 48
        },
        "pad_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Pad width [μm]",
            "default": 20
        },
        "pad_length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Pad length [μm]",
            "default": 14
        },
        "pad_extra": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Bottom pad extra [μm]",
            "default": 2
        },
        "bridge_type": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Airbridge type",
            "default": "normal",
            "choices": [["normal", "normal"]]
        },
    }

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
        self.cell.shapes(self.get_layer("airbridge pads")).insert(shape)

        # bottom layer lower pad
        self.cell.shapes(self.get_layer("airbridge pads")).insert(pya.DTrans.M0 * shape)

        # protection layer
        self.cell.shapes(self.get_layer("ground grid avoidance")).insert(shape.sized(self.margin))
        self.cell.shapes(self.get_layer("ground grid avoidance")).insert(pya.DTrans.M0 * shape.sized(self.margin))

        # refpoints for connecting to waveguides
        self.add_port("a", pya.DPoint(0, l / 2))
        self.add_port("b", pya.DPoint(0, -l / 2))
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
        self.cell.shapes(self.get_layer("airbridge flyover")).insert(shape)

