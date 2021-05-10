# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
import logging
import sys
from pathlib import Path
import subprocess

from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import export_simulation_oas, cross_sweep_simulation, sweep_simulation
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.pya_resolver import pya
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout


class InternalPortCalibration(Simulation):
    """ Left half of the ground plane is etched away, and a waveguide is added from the center towards the right. """

    def build(self):
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(
            pya.DBox(pya.DPoint(self.box.left + 10, self.box.bottom + 10),
                     pya.DPoint(self.box.center().x, self.box.top - 10)))
        self.produce_waveguide_to_port(self.box.center(), pya.DPoint(self.box.right, self.box.center().y), 1, 'right')


# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

# Simulation parameters
sim_class = InternalPortCalibration
sim_parameters = {
    'name': 'port_sim',
    'use_internal_ports': True,
    'use_ports': True,
    'box': pya.DBox(pya.DPoint(0, 0), pya.DPoint(500, 500)),
    'waveguide_length': 10,
    'wafer_stack_type': "multiface",  # chip distance default at 8um
    'a': 3.5, #readout structure a in flip chip
    'b': 32  #readout structure b in flip chip
}
export_parameters = {
    'path': dir_path,
    'max_delta_s': 0.0001,
    'maximum_passes': 40,
    'frequency': 5,
    'sweep_start': 1,
    'sweep_end': 5,
    'sweep_count': 4,
    'exit_after_run': True
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# # Sweep simulations for variable geometry
# simulations = cross_sweep_simulation(layout, sim_class, sim_parameters, {
#     'a': [2, 4, 6, 8, 10, 12, 16, 20],
#     'b': [2, 4, 6, 10, 14, 18, 22, 30],
#     'waveguide_length': [1, 10, 20, 50, 100]
# })

#Fixed geometry simulation
simulations = sweep_simulation(layout, sim_class, sim_parameters, {
    'waveguide_length': [1, 10, 20, 50, 100]
})

# Export Ansys files
export_ansys(simulations, **export_parameters)

# Write and open oas file
subprocess.call(export_simulation_oas(simulations, dir_path), shell=True)
