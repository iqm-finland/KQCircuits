# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import math

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt

from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar


class Meander(Element):
    """The PCell declaration for a meandering waveguide.

    Defined by two points, total length and number of meanders. Uses the same bending radius as the underling waveguide.
    """

    # TODO Remove coordinates from PCell parameters.
    start = Param(pdt.TypeShape, "Start", pya.DPoint(-600, 0))
    end = Param(pdt.TypeShape, "End", pya.DPoint(600, 0))
    length = Param(pdt.TypeDouble, "Length", 3000, unit="μm")
    meanders = Param(pdt.TypeInt, "Number of meanders (at least 1)", 4)

    def coerce_parameters_impl(self):
        self.meanders = max(self.meanders, 1)

    def can_create_from_shape_impl(self):
        return self.shape.is_path()

    def parameters_from_shape_impl(self):
        points = [pya.DPoint(point * self.layout.dbu) for point in self.shape.each_point()]
        self.start = points[0]
        self.end = points[-1]

    def produce_impl(self):
        points = [pya.DPoint(0, 0)]
        l_direct = self.start.distance(self.end)
        l_rest = l_direct - self.meanders * 2 * self.r
        l_single_meander = (self.length - (l_rest - 2 * self.r) - (self.meanders * 2 + 2) * (math.pi / 2) * self.r - (
                    self.meanders - 1) * self.r * 2) / (2 * self.meanders)

        points.append(pya.DPoint(l_rest / 2, 0))
        for i in range(self.meanders):
            points.append(pya.DPoint(l_rest / 2 + i * 2 * self.r, ((-1) ** (i % 2)) * (l_single_meander + 2 * self.r)))
            points.append(
                pya.DPoint(l_rest / 2 + (i + 1) * 2 * self.r, ((-1) ** (i % 2)) * (l_single_meander + 2 * self.r)))
        points.append(pya.DPoint(l_direct - l_rest / 2, 0))
        points.append(pya.DPoint(l_direct, 0))
        # print(set(points))
        waveguide = self.add_element(WaveguideCoplanar,
            path=pya.DPath(points, 1.),
            r=self.r,
            face_ids=self.face_ids,
            n=self.n,
            a=self.a,
            b=self.b
        )

        angle = 180 / math.pi * math.atan2(self.end.y - self.start.y, self.end.x - self.start.x)
        transf = pya.DCplxTrans(1, angle, False, pya.DVector(self.start))
        self.insert_cell(waveguide, transf)
