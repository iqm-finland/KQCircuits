# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from autologging import logged, traced
from kqcircuits.squids.squid import Squid
from kqcircuits.util.symmetric_polygons import polygon_with_vsym


@traced
@logged
class Sim(Squid):
    """The PCell declaration for a simulation type SQUID.

    Origin at the center of junction layer bottom edge.

    """
    version = 1

    def produce_impl(self):

        trans = pya.DTrans(0.0, 0.0)
        self._produce_ground_metal_shapes(trans)
        # refpoints
        self.refpoints["origin_squid"] = pya.DPoint(0, 0)
        self.refpoints["port_squid_a"] = pya.DPoint(0, 20)
        self.refpoints["port_squid_b"] = pya.DPoint(0, 12)
        self.refpoints["port_common"] = pya.DPoint(0, 33)

        super().produce_impl()

    def _produce_ground_metal_shapes(self, trans):
        """Produces hardcoded shapes in metal gap and metal addition layers."""
        # metal additions bottom
        bottom_pts = [
            pya.DPoint(-4, 0),
            pya.DPoint(-4, 12),
            pya.DPoint(4, 12),
            pya.DPoint(4, 0)
        ]
        shape = polygon_with_vsym(bottom_pts)
        self.cell.shapes(self.get_layer("base_metal_addition")).insert(trans*shape)
        # metal additions top
        top_pts = [
            pya.DPoint(-4, 20),
            pya.DPoint(-4, 33),
            pya.DPoint(4, 33),
            pya.DPoint(4, 20)
        ]
        shape = polygon_with_vsym(top_pts)
        self.cell.shapes(self.get_layer("base_metal_addition")).insert(trans*shape)
        # add ground grid avoidance
        w = self.cell.dbbox().width()
        h = self.cell.dbbox().height()
        protection = pya.DBox(-w / 2 - self.margin, - self.margin, w / 2 + self.margin, h + self.margin)
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(trans*protection)
