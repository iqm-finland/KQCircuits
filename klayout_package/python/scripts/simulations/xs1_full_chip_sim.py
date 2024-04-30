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


from pathlib import Path
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import export_simulation_oas
from kqcircuits.simulations.single_xmons_full_chip_sim import SingleXmonsFullChipSim
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, open_with_klayout_or_default_application


use_elmer = True
use_sbatch = False

launchers = True  # True includes bonding pads and tapers, false includes only waveguides
target_frequency = 5.0  # GHz, can also be list

if use_elmer:
    dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_elmer")
else:
    dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_hfss")

# Simulation parameters
sim_class = SingleXmonsFullChipSim  # pylint: disable=invalid-name

sim_parameters = {
    "name": "xs1_full_chip_sim",
    "use_ports": True,
    "launchers": launchers,
    "use_test_resonators": True,  # True makes XS1, false makes XS2
    "n": 16,  # Reduce number of point in waveguide corners
    "port_size": 900 if launchers else 200,
}

if use_elmer:
    mesh_size = {
        "global_max": 200.0,
        "1t1_gap": 50.0,
        "1t1_airbridge_flyover": 50.0,
        "1t1_airbridge_pads": 50.0,
        "1t1_signal": 50.0,
        "1t1_ground": 200.0,
        "substrate": 200.0,
        "vacuum": 200.0,
    }

    export_parameters_elmer = {
        "path": dir_path,
        "tool": "wave_equation",
        "frequency": target_frequency,
    }

    workflow = {
        "run_gmsh_gui": False,
        "run_elmergrid": True,
        "run_elmer": True,
        "run_paraview": False,
        "python_executable": "python",
        "gmsh_n_threads": -1,  #  Number of omp threads in gmsh
        "elmer_n_processes": -1,  # Number of dependent processes (tasks) in elmer
        "elmer_n_threads": 1,  # Number of omp threads per process in elmer
    }
    if use_sbatch:
        # if  simulation is run in a HPC system with SLURM, the settings can be given here
        # See hanger_resonator_sim.py for explanation of each option
        workflow["sbatch_parameters"] = {
            "--account": "project_0",
            "--partition": "test",
            "n_workers": 1,
            "max_threads_per_node": 40,
            "elmer_n_processes": 20,
            "elmer_n_threads": 1,
            "elmer_mem": "64G",
            "elmer_time": "00:30:00",
            "gmsh_n_threads": 20,
            "gmsh_mem": "64G",
            "gmsh_time": "00:30:00",
        }

else:
    export_parameters_ansys = {
        "path": dir_path,
        "frequency": target_frequency,
        "max_delta_s": 0.001,
        "sweep_start": 1,
        "sweep_end": 10,
        "sweep_count": 1001,
        "maximum_passes": 20,
        "exit_after_run": False,
    }


# Create simulation
simulations = [sim_class(pya.Layout(), **sim_parameters)]

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))


if use_elmer:
    export_elmer(simulations, **export_parameters_elmer, mesh_size=mesh_size, workflow=workflow)
else:
    export_ansys(simulations, **export_parameters_ansys)
