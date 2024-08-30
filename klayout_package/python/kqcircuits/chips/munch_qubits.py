# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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

import logging

from kqcircuits.chips.chip import Chip
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.elements.meander import Meander
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node
from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter
from kqcircuits.pya_resolver import pya
from kqcircuits.qubits.circular_transmon_single_island import CircularTransmonSingleIsland
from kqcircuits.qubits.double_pads import DoublePads
from kqcircuits.util.coupler_lib import cap_params
from kqcircuits.util.parameters import Param, pdt, add_parameters_from


@add_parameters_from(Chip, name_chip="EM1")
@add_parameters_from(
    DoublePads,
    coupler_extent=[150, 20],
    island1_extent=[1000, 200],
    island2_extent=[1000, 200],
    island_island_gap=200,
    ground_gap=[1400, 900],
    drive_position=[-1100, 400],
)
class MunchQubits(Chip):
    """Demonstration chip with two circular single island qubits, one floating island qubit, three readout resonators,
    one probe line, three drivelines and one resonant coupler.

    """

    # Readout parameters
    readout_res_lengths = Param(pdt.TypeList, "Readout resonator lengths", [11500, 12700, 8000], unit="[μm]")
    kappa_finger_control = Param(
        pdt.TypeList, "Finger control for the input capacitor", [3.32, 4.21, 1.46], unit="[μm]"
    )
    # Coupling parameters
    coupler_length = Param(pdt.TypeDouble, "Resonant coupler length", 9800, unit="µm")
    # Circular qubit 1 parameters
    couplers_a_qb1 = Param(pdt.TypeList, "Width of the coupler waveguide's center conductors", [10, 3], unit="[μm]")
    couplers_b_qb1 = Param(pdt.TypeList, "Width of the coupler waveguide's gaps", [6, 32], unit="[μm]")
    couplers_angle_qb1 = Param(
        pdt.TypeList,
        "Positioning angles of the couplers, where 0deg corresponds to positive x-axis",
        [225, 315],
        unit="[degrees]",
    )
    couplers_width_qb1 = Param(pdt.TypeList, "Radial widths of the arc couplers", [30, 50], unit="[μm]")
    couplers_arc_amplitude_qb1 = Param(pdt.TypeList, "Couplers angular extension", [25, 65], unit="[degrees]")
    # Circular qubit 2 parameters
    couplers_a_qb2 = Param(pdt.TypeList, "Width of the coupler waveguide's center conductors", [10, 3], unit="[μm]")
    couplers_b_qb2 = Param(pdt.TypeList, "Width of the coupler waveguide's gaps", [6, 32], unit="[μm]")
    couplers_angle_qb2 = Param(
        pdt.TypeList,
        "Positioning angles of the couplers, where 0deg corresponds to positive x-axis",
        [315, 225],
        unit="[degrees]",
    )
    couplers_width_qb2 = Param(pdt.TypeList, "Radial widths of the arc couplers", [30, 50], unit="[μm]")
    couplers_arc_amplitude_qb2 = Param(pdt.TypeList, "Couplers angular extension", [35, 65], unit="[degrees]")

    drive_line_offsets = Param(
        pdt.TypeList, "Distance between the end of a drive line and the qubit pair", [550.0] * 2, unit="[µm]"
    )

    # Floating double pad qubit 3 parameters are added instead as @add_parameters_from the element since there is only
    # one  qubit, they will be passed automatically to the element when added

    def build(self):
        # Define launchpads positioning and function
        launcher_assignments = {
            1: "DL-QB1",
            2: "DL-QB2",
            3: "PL-1-OUT",
            5: "DL-QB3",
            8: "PL-1-IN",
        }
        # Use an 8 port default launcher
        self.produce_launchers("SMA8", launcher_assignments)
        self.produce_qubits()
        self.produce_coupler()
        self.produce_probeline()
        self.produce_readout_resonators()
        self.produce_drivelines()

    def produce_qubits(self):
        # Position the circular qubits
        transformations = [pya.DCplxTrans(1, 0, False, 3500, 7000), pya.DCplxTrans(1, 0, False, 6500, 7000)]
        drive_angles = [110, 70]

        # Make a function to add a single circular qubit
        def produce_circular_qubit(
            name,
            trans,
            couplers_a,
            couplers_b,
            couplers_angle,
            couplers_width,
            couplers_arc_amplitude,
            drive_angle,
            drive_line_offset,
        ):
            qubit_cell = self.add_element(
                CircularTransmonSingleIsland,
                r_island=300,
                ground_gap=200,
                squid_angle=90,
                drive_angle=drive_angle,
                drive_distance=float(drive_line_offset),
                couplers_r=400,
                couplers_a=list(map(float, couplers_a)),
                couplers_b=list(map(float, couplers_b)),
                couplers_angle=list(map(float, couplers_angle)),
                couplers_width=list(map(float, couplers_width)),
                couplers_arc_amplitude=list(map(float, couplers_arc_amplitude)),
            )
            _, _ = self.insert_cell(qubit_cell, trans, name, rec_levels=None)

        # Insert both circular qubits
        produce_circular_qubit(
            "QB1",
            transformations[0],
            self.couplers_a_qb1,
            self.couplers_b_qb1,
            self.couplers_angle_qb1,
            self.couplers_width_qb1,
            self.couplers_arc_amplitude_qb1,
            drive_angles[0],
            self.drive_line_offsets[0],
        )
        produce_circular_qubit(
            "QB2",
            transformations[1],
            self.couplers_a_qb2,
            self.couplers_b_qb2,
            self.couplers_angle_qb2,
            self.couplers_width_qb2,
            self.couplers_arc_amplitude_qb2,
            drive_angles[1],
            self.drive_line_offsets[1],
        )

        # Add now the floating island qubit
        qubit_cell = self.add_element(DoublePads)
        _, _ = self.insert_cell(qubit_cell, pya.DCplxTrans(1, 180, False, 5000, 4000), "QB3", rec_levels=None)

    def produce_coupler(self):
        # Insert a fixed coupler of a variable meander size in between qubits
        _, _, length = WaveguideComposite.produce_fixed_length_waveguide(
            self,
            lambda x: [
                Node(self.refpoints["QB1_port_coupler_2"]),
                Node(self.refpoints["QB1_port_coupler_2_corner"], n_bridges=1),
                Node(pya.DPoint(4500, 6500), n_bridges=2),
                Node(pya.DPoint(5500, 6500), length_before=x, n_bridges=6),
                Node(self.refpoints["QB2_port_coupler_2_corner"], n_bridges=2),
                Node(self.refpoints["QB2_port_coupler_2"], n_bridges=1),
            ],
            initial_guess=5000,
            length=self.coupler_length,
            a=float(self.couplers_a_qb1[1]),
            b=float(self.couplers_b_qb1[1]),
            term1=0,
            term2=0,
        )

        logging.info(f"Coupler line length: {length:.2f}")

    def produce_probeline(self):
        # Make the probeline pass through the resonators tees
        probeline = self.add_element(
            WaveguideComposite,
            nodes=[
                Node(self.refpoints["PL-1-IN_base"]),
                Node(self.refpoints["PL-1-IN_port_corner"], n_bridges=1),
                Node(pya.DPoint(self.refpoints["QB1_base"].x - 1000, 1500), n_bridges=4),
                Node(
                    pya.DPoint(self.refpoints["QB1_base"].x, 1500),
                    WaveguideCoplanarSplitter,
                    align=("port_a", "port_c"),
                    angles=[180, 90, 0],
                    lengths=[50, 150, 50],
                    inst_name="QB1_tee",
                    use_airbridges=True,
                    n_bridges=1,
                ),
                Node(
                    pya.DPoint(5000, 1500),
                    WaveguideCoplanarSplitter,
                    align=("port_a", "port_c"),
                    angles=[180, 90, 0],
                    lengths=[50, 150, 50],
                    inst_name="QB3_tee",
                    use_airbridges=True,
                    n_bridges=2,
                ),
                Node(
                    pya.DPoint(self.refpoints["QB2_base"].x, 1500),
                    WaveguideCoplanarSplitter,
                    align=("port_a", "port_c"),
                    angles=[180, 90, 0],
                    lengths=[50, 150, 50],
                    inst_name="QB2_tee",
                    use_airbridges=True,
                    n_bridges=2,
                ),
                Node(pya.DPoint(self.refpoints["QB2_base"].x + 1000, 1500), n_bridges=1),
                Node(self.refpoints["PL-1-OUT_port_corner"], n_bridges=4),
                Node(self.refpoints["PL-1-OUT_base"], n_bridges=1),
            ],
            a=self.a,
            b=self.b,
            term1=0,
            term2=0,
        )
        self.insert_cell(probeline, inst_name="pl")

    def produce_drivelines(self):
        # Connect the drivelines to the qubit ports
        # Circular qubits
        for qubit_nr in range(1, 3):
            self.insert_cell(
                WaveguideComposite,
                nodes=[
                    Node(self.refpoints[f"DL-QB{qubit_nr}_base"]),
                    Node(self.refpoints[f"DL-QB{qubit_nr}_port_corner"], n_bridges=1),
                    Node(self.refpoints[f"DL-QB{qubit_nr}_port_corner"] + pya.DPoint(0, -1200), n_bridges=1),
                    Node(self.refpoints[f"QB{qubit_nr}_port_drive_corner"], n_bridges=1),
                    Node(self.refpoints[f"QB{qubit_nr}_port_drive"]),
                ],
                term2=self.b,
            )
            # Double pad qubit
            airbridge_crossing_coordinate = (
                self.refpoints["pl_QB2_tee_base"] - self.refpoints["pl_QB3_tee_base"]
            ) / 2 + self.refpoints["pl_QB3_tee_base"]
            self.insert_cell(
                WaveguideComposite,
                nodes=[
                    Node(self.refpoints["DL-QB3_base"]),
                    Node(self.refpoints["DL-QB3_port_corner"], n_bridges=1),
                    Node(airbridge_crossing_coordinate + pya.DVector(0, -300), n_bridges=1),
                    Node(airbridge_crossing_coordinate, AirbridgeConnection, n_bridges=1),
                    Node(airbridge_crossing_coordinate + pya.DVector(0, 200), n_bridges=1),
                    Node(
                        pya.DPoint(
                            self.refpoints["QB3_port_drive_corner"].x,
                            (airbridge_crossing_coordinate + pya.DVector(0, 300)).y,
                        ),
                    ),
                    Node(self.refpoints["QB3_port_drive_corner"], n_bridges=2),
                    Node(self.refpoints["QB3_port_drive"]),
                ],
                term2=self.b,
            )

    def produce_readout_resonators(self):
        # Break down the resonator in few parts for simplicity
        tee_angles = [90, 90, 90]  # Coupling port direction at the probeline
        for i, t_angle in enumerate(tee_angles):
            capacitor = self.add_element(
                **cap_params(
                    fingers=float(self.kappa_finger_control[i]),
                    coupler_type="smooth",
                    element_key="cls",
                    fixed_length=160,
                )
            )
            _, cplr_ref = self.insert_cell(
                capacitor,
                trans=pya.DCplxTrans(1, t_angle, False, 0, 0),
                align_to=f"pl_QB{i + 1}_tee_port_b",
                align="port_a",
            )
            # Add the lower part of the resonator, align it, measure it
            # Qubits ports are called slightly different for the circular qubits and the double pad
            qubits_couplers_corners = [f"QB{i + 1}_port_coupler_1_corner"] * 2 + [f"QB{i + 1}_port_cplr_corner"]
            qubits_couplers_refp = [f"QB{i + 1}_port_coupler_1"] * 2 + [f"QB{i + 1}_port_cplr"]
            resonator_bottom, _ = self.insert_cell(
                WaveguideComposite,
                nodes=[
                    Node(cplr_ref["port_b"]),
                    Node(cplr_ref["port_b_corner"]),
                    Node(pya.DPoint(self.refpoints[qubits_couplers_corners[i]].x, cplr_ref["port_b_corner"].y + 100)),
                    Node(
                        pya.DPoint(self.refpoints[qubits_couplers_corners[i]].x, cplr_ref["port_b_corner"].y + 200),
                        n_bridges=1,
                    ),
                ],
                inst_name=f"resonator_bottom_{i + 1}",
            )
            length_nonmeander_bottom = resonator_bottom.cell.length()
            # Add the upper part of the resonator, align it, measure it
            resonator_top, _ = self.insert_cell(
                WaveguideComposite,
                nodes=[
                    Node(self.refpoints[qubits_couplers_refp[i]]),
                    Node(self.refpoints[qubits_couplers_corners[i]]),
                    Node(self.refpoints[qubits_couplers_corners[i]] + pya.DPoint(0, -300), n_bridges=1),
                ],
                inst_name=f"resonator_top_{i + 1}",
            )
            length_nonmeander_top = resonator_top.cell.length()
            # Add the missing part in the center in the correct length
            meander, _ = self.insert_cell(
                Meander,
                start_point=self.refpoints[qubits_couplers_corners[i]] + pya.DPoint(0, -300),
                end_point=self.refpoints[f"resonator_bottom_{i + 1}_port_b"],
                length=float(self.readout_res_lengths[i]) - length_nonmeander_top - length_nonmeander_bottom,
                n_bridges=18,
            )
            logging.info(
                f"Resonator QB{i + 1} length: "
                f"{length_nonmeander_bottom + length_nonmeander_top + meander.cell.length()}"
            )
