#!/usr/bin/env python3
# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

"""
Simulation script for Circular Transmon Single Island EPR analysis using MER method.

This script configures and exports an EPR simulation for the Circular Transmon Single Island qubit,
using the Metal-edge-corrected (MER) simulation method to calculate Energy Participation Ratio.
"""

import logging
import numpy as np
from pathlib import Path

from kqcircuits.defaults import TMP_PATH
from kqcircuits.qubits.circular_transmon_single_island import CircularTransmonSingleIsland
from kqcircuits.simulations.epr_simulation import EprSimulation
from kqcircuits.simulations.export.simulation_export import export_simulation_oas
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout


def create_simulation():
    """Create and configure the EPR simulation for Circular Transmon Single Island."""
    
    # Get layout
    layout = get_active_or_new_layout()
    
    # Create simulation with single qubit
    simulations = [
        EprSimulation(
            layout,
            name="circular_transmon_single_island_epr_sim",
            qubit=CircularTransmonSingleIsland,
            junction_type="Sim",  # Use simulation junction (empty pads)
            
            # Qubit parameters - can be modified for parameter sweeps
            r_island=120,
            ground_gap=80,
            squid_angle=120,
            couplers_r=150,
            couplers_a=[10, 3, 4.5],
            couplers_b=[6, 32, 20],
            couplers_angle=[340, 60, 210],
            couplers_width=[10, 20, 30],
            couplers_arc_amplitude=[35, 45, 15],
            drive_angle=300,
            drive_distance=400,
            
            # Simulation parameters
            box=2000,
            substrate_height=550,
            tls_sheet_approximation=True,
            tls_loss_tangent=1e-3,
            
            # Export settings
            ignore_ports=True,  # Ignore waveguide ports for simplified simulation
        )
    ]
    
    # Uncomment and modify the following block for parameter sweeps:
    """
    # Example parameter sweep - vary island radius and ground gap
    simulations = []
    for r_island in [100, 120, 140]:
        for ground_gap in [60, 80, 100]:
            sim = EprSimulation(
                layout,
                name=f"circular_transmon_single_island_epr_sim_r{r_island}_g{ground_gap}",
                qubit=CircularTransmonSingleIsland,
                junction_type="Sim",
                r_island=r_island,
                ground_gap=ground_gap,
                # ... other parameters as above
            )
            simulations.append(sim)
    """
    
    return simulations


def main():
    """Main simulation export function."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Create output directory
    output_path = create_or_empty_tmp_directory("circular_transmon_single_island_epr_sim_output")
    
    # Create simulations
    simulations = create_simulation()
    
    # Export simulation geometry to OAS format for visualization
    export_simulation_oas(simulations, output_path)
    logging.info(f"Exported simulation geometry to {output_path}")
    
    # Export to Elmer FEM format for simulation
    export_elmer(
        simulations, 
        output_path, 
        tool="capacitance",
        linear_system_method="mg",
        p_element_order=3,
        mesh_size={"vacuum": 500, "signal": 5, "ground": 5, "substrate": 100},
    )
    logging.info(f"Exported Elmer simulation files to {output_path}")
    
    print("\nSimulation export completed successfully!")
    print(f"Output directory: {output_path}")
    print("\nTo run the simulation:")
    print("1. Run: kqc sim circular_transmon_single_island_epr_sim.py")
    print("2. Or run in quiet mode: kqc sim circular_transmon_single_island_epr_sim.py -q")
    print(f"3. Results will be saved in: {output_path}")
    print("4. EPR results will be in: circular_transmon_single_island_epr_sim_output_epr.csv")


if __name__ == "__main__":
    main()
