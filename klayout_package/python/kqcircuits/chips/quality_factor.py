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


from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt

from kqcircuits.chips.chip import Chip
from kqcircuits.defaults import default_airbridge_type, default_sampleholders
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.quarter_wave_cpw_resonator import QuarterWaveCpwResonator


class QualityFactor(Chip):
    """The PCell declaration for a QualityFactor chip."""

    res_lengths = Param(
        pdt.TypeList,
        "Resonator lengths",
        [5434, 5429, 5374, 5412, 5493, 5589],
        unit="[μm]",
        docstring="Physical length of resonators [μm]",
    )
    n_fingers = Param(
        pdt.TypeList, "Number of fingers of the coupler", [4, 4, 2, 4, 4, 4], docstring="Fingers in planar capacitors"
    )
    l_fingers = Param(
        pdt.TypeList,
        "Length of fingers",
        [23.1, 9.9, 14.1, 10, 21, 28],
        unit="[μm]",
        docstring="Length of the capacitor fingers [μm]",
    )
    type_coupler = Param(
        pdt.TypeList, "Coupler types", ["interdigital", "interdigital", "interdigital", "gap", "gap", "gap"]
    )
    n_ab = Param(pdt.TypeList, "Number of resonator airbridges", [5, 0, 5, 5, 5, 5])
    res_term = Param(
        pdt.TypeList,
        "Resonator termination type",
        ["galvanic", "galvanic", "galvanic", "airbridge", "airbridge", "airbridge"],
    )
    res_beg = Param(
        pdt.TypeList,
        "Resonator beginning type",
        ["galvanic", "galvanic", "galvanic", "airbridge", "airbridge", "airbridge"],
    )
    res_a = Param(
        pdt.TypeList,
        "Resonator waveguide center conductor width",
        [5, 10, 20, 5, 10, 20],
        unit="[μm]",
        docstring="Width of the center conductor in the resonators [μm]",
    )
    res_b = Param(
        pdt.TypeList,
        "Resonator waveguide gap width",
        [3, 6, 12, 3, 6, 12],
        unit="[μm]",
        docstring="Width of the gap in the resonators [μm]",
    )
    tl_airbridges = Param(pdt.TypeBoolean, "Airbridges on transmission line", True)
    res_airbridge_types = Param(pdt.TypeList, "Airbridge type for each resonator", default=[default_airbridge_type] * 6)
    sample_holder_type = Param(pdt.TypeInt, "Sample holder type for the chip", "SMA8", choices=["SMA8", "ARD24"])
    marker_safety = Param(pdt.TypeDouble, "Distance between launcher and first curve", 1000, unit="μm")
    feedline_bend_distance = Param(pdt.TypeDouble, "Horizontal distance of feedline bend", 100, unit="μm")
    resonators_both_sides = Param(pdt.TypeBoolean, "Place resonators on both sides of feedline", False)
    max_res_len = Param(
        pdt.TypeDouble,
        "Maximal straight length of resonators",
        1e30,
        unit="μm",
        docstring="Resonators exceeding this length become meandering",
    )
    ground_grid_in_trace = Param(pdt.TypeList, "Include ground-grid in the trace", [0] * 6)
    # override box to have hidden=False and allow GUI editing
    box = Param(pdt.TypeShape, "Border", pya.DBox(pya.DPoint(0, 0), pya.DPoint(10000, 10000)))

    def build(self):
        # Interpretation of parameter lists
        res_lengths = [float(foo) for foo in self.res_lengths]
        res_a = [float(foo) for foo in self.res_a]
        res_b = [float(foo) for foo in self.res_b]
        n_fingers = [float(foo) for foo in self.n_fingers]
        type_coupler = self.type_coupler
        n_ab = [int(foo) for foo in self.n_ab]
        l_fingers = [float(foo) for foo in self.l_fingers]
        res_term = self.res_term
        res_beg = self.res_beg

        # center the resonators in the chip regardless of size
        max_res_len = min(max(res_lengths), self.max_res_len)
        chip_side = self.box.p2.y - self.box.p1.y
        if self.resonators_both_sides:
            wg_top_y = chip_side / 2
        else:
            wg_top_y = (chip_side + max_res_len) / 2

        # support resizable chip keeping pad distances from the top constant
        launchers = None
        if self.sample_holder_type == "ARD24":
            launchers = self.produce_n_launchers(
                **{**default_sampleholders["ARD24"], "pad_pitch": (chip_side - 4000) / 5, "chip_box": self.box},
                launcher_assignments={24: "PL-1-IN", 7: "PL-1-OUT"},
            )
        elif self.sample_holder_type == "SMA8":
            launchers = self.produce_n_launchers(
                **{**default_sampleholders["SMA8"], "pad_pitch": chip_side - 2 * 2800, "chip_box": self.box},
                launcher_assignments={8: "PL-1-IN", 3: "PL-1-OUT"},
            )

        # Define start and end of feedline
        points_fl = [launchers["PL-1-IN"][0]]
        if abs(launchers["PL-1-IN"][0].y - wg_top_y) > 1:
            # Bend in the feedline needed
            points_fl += [
                launchers["PL-1-IN"][0] + pya.DVector(self.r + self.marker_safety, 0),
                pya.DPoint(
                    launchers["PL-1-IN"][0].x + self.r + self.feedline_bend_distance + self.marker_safety, wg_top_y
                ),
            ]
            points_fl_end = [
                pya.DPoint(
                    launchers["PL-1-OUT"][0].x - self.r - self.feedline_bend_distance - self.marker_safety, wg_top_y
                ),
                launchers["PL-1-OUT"][0] + pya.DVector(-self.r - self.marker_safety, 0),
            ]
        elif self.marker_safety > 0:
            points_fl += [launchers["PL-1-IN"][0] + pya.DVector(self.marker_safety, 0)]
            points_fl_end = [
                launchers["PL-1-OUT"][0] + pya.DVector(-self.marker_safety, 0),
            ]
        else:
            points_fl_end = []

        points_fl_end += [launchers["PL-1-OUT"][0]]

        tl_start = points_fl[-1]
        tl_end = points_fl_end[0]

        resonators = len(self.res_lengths)
        v_res_step = (tl_end - tl_start) * (1.0 / resonators)

        for i in range(resonators):
            resonator_up = self.resonators_both_sides and (i % 2) == 0

            # Add resonator element
            _, refp = self.insert_cell(
                QuarterWaveCpwResonator,
                trans=pya.DTrans(2 if resonator_up else 0, False, tl_start + (i + 0.5) * v_res_step),
                probeline_length=120.0,
                resonator_length=res_lengths[i],
                max_res_len=max_res_len,
                res_beg=res_beg[i],
                res_term=res_term[i],
                n_ab=n_ab[i],
                res_airbridge_types=str(self.res_airbridge_types[i]),
                tl_airbridges=self.tl_airbridges,
                n_fingers=n_fingers[i],
                l_fingers=l_fingers[i],
                ground_grid_in_trace=int(self.ground_grid_in_trace[i]),
                type_coupler=type_coupler[i],
                res_a=res_a[i],
                res_b=res_b[i],
            )

            # Add segment of feedline
            self.insert_cell(
                WaveguideCoplanar,
                **{
                    **self.cell.pcell_parameters_by_name(),
                    **{
                        "path": pya.DPath(points_fl + [refp["port_b" if resonator_up else "port_a"]], 1),
                        "term2": 0,
                        "ground_grid_in_trace": False,
                    },
                },
            )
            points_fl = [refp["port_a" if resonator_up else "port_b"]]

        # Add the last segment of feedline
        self.insert_cell(
            WaveguideCoplanar,
            **{
                **self.cell.pcell_parameters_by_name(),
                **{"path": pya.DPath(points_fl + points_fl_end, 1), "term2": 0, "ground_grid_in_trace": False},
            },
        )
