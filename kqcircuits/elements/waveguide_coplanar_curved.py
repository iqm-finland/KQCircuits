# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import math

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.element import Element


def up_mod(a, per):
    # Finds remainder in the same direction as periodicity
    if (a * per > 0):
        return a % per
    else:
        return a - per * math.floor(a / per)


def arc(R, start, stop, n):
    pts = []
    last = start

    alpha_rel = up_mod(stop - start, math.pi * 2)  # from 0 to 2 pi
    alpha_step = 2 * math.pi / n * (
        -1 if alpha_rel > math.pi else 1)  # shorter dir  n_steps = math.floor((2*math.pi-alpha_rel)/abs(alpha_step) if alpha_rel > math.pi else alpha_rel/abs(alpha_step))
    n_steps = math.floor(
        (2 * math.pi - alpha_rel) / abs(alpha_step) if alpha_rel > math.pi else alpha_rel / abs(alpha_step))

    alpha = start

    for i in range(0, n_steps + 1):
        pts.append(pya.DPoint(R * math.cos(alpha), R * math.sin(alpha)))
        alpha += alpha_step
        last = alpha

    if last != stop:
        alpha = stop
        pts.append(pya.DPoint(R * math.cos(alpha), R * math.sin(alpha)))

    return pts


class WaveguideCoplanarCurved(Element):
    """
  The PCell declaration of a curved segment of a coplanar waveguide.
  
  Cordinate origin is left at the center of the arch.
  """

    PARAMETERS_SCHEMA = {
        "alpha": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Curve angle (rad)",
            "default": math.pi
        },
        "length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Actual length (um)",
            "default": 0,
            "readonly": True
        }
    }

    def __init__(self):
        super().__init__()

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "WaveguideCopCurve(a=" + ('%.1f' % self.a) + ",b=" + ('%.1f' % self.b) + ")"

    def coerce_parameters_impl(self):
        # Update length
        self.length = self.r * abs(self.alpha)

    def can_create_from_shape_impl(self):
        return False

    def parameters_from_shape_impl(self):
        None

    def produce_impl(self):
        # Refpoint in the center of the turn
        alphastart = 0
        alphastop = self.alpha

        # Left gap
        pts = []
        R = self.r - self.a / 2
        pts += arc(R, alphastart, alphastop, self.n)
        R = self.r - self.a / 2 - self.b
        pts += arc(R, alphastop, alphastart, self.n)
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.layout.layer(self.face()["base metal gap wo grid"])).insert(shape)
        # Right gap
        pts = []
        R = self.r + self.a / 2
        pts += arc(R, alphastart, alphastop, self.n)
        R = self.r + self.a / 2 + self.b
        pts += arc(R, alphastop, alphastart, self.n)
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.layout.layer(self.face()["base metal gap wo grid"])).insert(shape)
        # Protection layer
        pts = []
        R = self.r - self.a / 2 - self.b - self.margin
        pts += arc(R, alphastart, alphastop, self.n)
        R = self.r + self.a / 2 + self.b + self.margin
        pts += arc(R, alphastop, alphastart, self.n)
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.layout.layer(self.face()["ground grid avoidance"])).insert(shape)
        # Annotation
        R = self.r
        pts = arc(R, alphastart, alphastop, self.n)
        shape = pya.DPath(pts, self.a + 2 * self.b)
        self.cell.shapes(self.layout.layer(self.la)).insert(shape)
