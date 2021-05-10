# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from autologging import logged, traced

from kqcircuits.elements.airbridges.airbridge import Airbridge


@traced
@logged
class AirbridgeRectangular(Airbridge):
    """PCell declaration for a rectangular airbridge.

    Origin is at the geometric center. The airbridge is in vertical direction.

    Bottom parts of pads in bottom layer, bridge and top parts of pads in top layer. Pads and bridge are rectangular.
    Refpoints "port_a" and "port_b" at top pad points closest to origin.
    """

    default_type = "Airbridge Rectangular"

    bridge_width = Param(pdt.TypeDouble, "Bridge width", 20, unit="μm")

    def produce_impl(self):
        # shorthand
        (w, h, l, b, e) = (self.pad_width, self.pad_length, self.bridge_length, self.bridge_width, self.pad_extra)

        pts = [
            pya.DPoint(-self.pad_width / 2 - e, l / 2 - e),
            pya.DPoint(-self.pad_width / 2 - e, h + l / 2 + e),
            pya.DPoint(self.pad_width / 2 + e, h + l / 2 + e),
            pya.DPoint(self.pad_width / 2 + e, l / 2 - e),
        ]
        self._produce_bottom_pads(pts)

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
        self._produce_top_pads_and_bridge(pts)
