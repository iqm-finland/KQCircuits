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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).

import math
import logging

from kqcircuits.util.parameters import Param, pdt
from kqcircuits.qubits.qubit import Qubit
from kqcircuits.pya_resolver import pya
from kqcircuits.util.refpoints import JunctionSimPort, WaveguideToSimPort


class SwissmonExperimental(Qubit):
    """
    Experimental Swissmon-style qubit.

    This version adds:
    - lightweight geometry validation
    - optional debug marker generation
    - extra refpoint annotations
    """

    arm_length = Param(pdt.TypeList, "Arm length (um, WNES))", [150.0] * 4)
    arm_width = Param(pdt.TypeList, "Arm metal width (um, WNES)", [24, 24, 24, 24])
    gap_width = Param(pdt.TypeList, "Arm gap width (um, WNES)", [12, 12, 12, 12])

    debug_mode = Param(pdt.TypeBoolean, "Enable debug markers", False)

    island_r = Param(pdt.TypeDouble, "Center island rounding radius", 5, unit="μm")

    def build(self):
        self._validate_geometry()
        self._build_cross()

        if self.debug_mode:
            self._add_debug_marker()

    def _validate_geometry(self):
        """
        Lightweight geometry validation.

        Intended only as a safety helper during layout experiments.
        """
        for idx, value in enumerate(self.arm_length):
            if float(value) <= 0:
                logging.warning("Arm length %d is non-positive", idx)

        for idx, value in enumerate(self.gap_width):
            if float(value) < 2:
                logging.warning("Gap width %d is unusually small", idx)

    def _build_cross(self):
        """
        Construct a simplified Swissmon-style cross.
        """

        [ww, wn, we, ws] = [float(width) / 2 for width in self.arm_width]
        l = [float(length) for length in self.arm_length]

        points = [
            pya.DPoint(wn, we),
            pya.DPoint(l[2], we),
            pya.DPoint(l[2], -we),
            pya.DPoint(ws, -we),
            pya.DPoint(ws, -l[3]),
            pya.DPoint(-ws, -l[3]),
            pya.DPoint(-ws, -ww),
            pya.DPoint(-l[0], -ww),
            pya.DPoint(-l[0], ww),
            pya.DPoint(-wn, ww),
            pya.DPoint(-wn, l[1]),
            pya.DPoint(wn, l[1]),
        ]

        poly = pya.DPolygon(points)
        rounded = poly.round_corners(self.island_r, self.island_r, self.n)

        region = pya.Region([rounded.to_itype(self.layout.dbu)])

        self.cell.shapes(
            self.get_layer("base_metal_gap_wo_grid")
        ).insert(region)

        for idx, point in enumerate(points):
            self.refpoints[f"debug_cross_{idx:02d}"] = point

        self.refpoints["cross_center"] = pya.DPoint(0, 0)

    def _add_debug_marker(self):
        """
        Adds a small visual debug marker at the center.
        """

        marker = pya.DBox(-5, -5, 5, 5)

        self.cell.shapes(
            self.get_layer("waveguide_path")
        ).insert(marker)

    @classmethod
    def get_sim_ports(cls, simulation):
        return [
            JunctionSimPort(),
            WaveguideToSimPort("port_left", side="left"),
            WaveguideToSimPort("port_top", side="top"),
            WaveguideToSimPort("port_right", side="right"),
        ]
