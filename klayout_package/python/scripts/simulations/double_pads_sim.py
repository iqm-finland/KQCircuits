# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).

import logging
import sys
from pathlib import Path
from itertools import product

import numpy as np

from kqcircuits.simulations.double_pads import DoublePadsSim
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.simulation_export import sweep_simulation
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout


sim_tools = ['elmer', 'eigenmode', 'q3d']

# Simulation parameters
sim_class = DoublePadsSim  # pylint: disable=invalid-name
sim_parameters = {
    'name': 'double_pads',
    'use_internal_ports': True,
    'use_ports': True,
    'wafer_stack_type': 'planar',
    'box': pya.DBox(pya.DPoint(0, 0), pya.DPoint(2000, 2000)),

    'internal_island_ports': True  # DoublePads specific
}

for sim_tool in sim_tools:
    dir_path = create_or_empty_tmp_directory(Path(__file__).stem + f'_output_{sim_tool}')

    export_parameters_ansys = {
        'ansys_tool': sim_tool,
        'path': dir_path,
        'exit_after_run': True,
    }

    # Add eigenmode and Q3D specific settings
    export_parameters_ansys |= {
        'percent_error': 0.3,
        'maximum_passes': 18,
        'minimum_passes': 2,
        'minimum_converged_passes': 2,
    } if sim_tool == 'q3d' else {
        'max_delta_f': 0.5,

        # do two passes with tight mesh
        'gap_max_element_length': 10,
        'maximum_passes': 2,
        'minimum_passes': 1,
        'minimum_converged_passes': 1,

        # lossy eigenmode simulation settings
        'n_modes': 2,
        'frequency': 0.5,  # minimum allowed eigenfrequency
        'simulation_flags': ['pyepr'],

        # run T1 analysis with pyEPR between simulations
        'intermediate_processing_command': 'python "scripts/t1_estimate.py"',
        'participation_sheet_distance': 5e-3,  # in µm
        'thicken_participation_sheet_distance': None,

        # The values here are taken from the following literature:
        #
        # [1] J. Verjauw et al., ‘Investigation of Microwave Loss Induced by Oxide Regrowth in High-Q Niobium Resonators’,   # pylint: disable=line-too-long
        #     Phys. Rev. Applied, vol. 16, no. 1, p. 014018, Jul. 2021, doi: 10.1103/PhysRevApplied.16.014018.
        # [2] M. V. P. Altoé et al., ‘Localization and Mitigation of Loss in Niobium Superconducting Circuits’,
        #     PRX Quantum, vol. 3, no. 2, p. 020312, Apr. 2022, doi: 10.1103/PRXQuantum.3.020312.
        # [3] M. P. F. Graça et al., ‘Electrical analysis of niobium oxide thin films’,
        #     Thin Solid Films, vol. 585, pp. 95–99, Jun. 2015, doi: 10.1016/j.tsf.2015.02.047.
        # [4] C. Wang et al., ‘Surface participation and dielectric loss in superconducting qubits’,
        #     Appl. Phys. Lett., vol. 107, no. 16, p. 162601, Oct. 2015, doi: 10.1063/1.4934486.
        # [5] W. Woods et al., ‘Determining Interface Dielectric Losses in Superconducting Coplanar-Waveguide Resonators’,  # pylint: disable=line-too-long
        #     Phys. Rev. Applied, vol. 12, no. 1, p. 014012, Jul. 2019, doi: 10.1103/PhysRevApplied.12.014012.
        'substrate_loss_tangent': 5e-7,  # [5]
        'dielectric_surfaces': {
            'layerMA': {
                'tan_delta_surf': 9.9e-3,  # surface loss tangent [1]
                'th': 4.8e-9,  # thickness, [2]
                'eps_r': 8,  # relative permittivity, worst-case [3]
            },
            'layerMS': {
                'tan_delta_surf': 2.6e-3,  # [4]
                'th': 0.3e-9,  # estimate worst case, [2]
                'eps_r': 11.4,  # estimate worst case (permittivity of Si)
            },
            'layerSA': {
                'tan_delta_surf': 2.1e-3,  # [5, 1new]
                'th': 2.4e-9,  # [2]
                'eps_r': 4,  # [5]
            }
        },
    }

    export_parameters_elmer = {
        'tool': 'capacitance',
        'workflow': {
            'python_executable': 'python',
            'n_workers': 4,
            'elmer_n_processes': 4,
        },
        'gmsh_params': {
            'default_mesh_size': 50.,
            'gap_min_mesh_size': 2.,
            'gap_min_dist': 4.,
            'gap_max_dist': 50.,
            'port_min_mesh_size': 1.,
            'port_min_dist': 4.,
            'port_max_dist': 50.,
            'algorithm': 5,
            'gmsh_n_threads': 4,
            'show': False,
        }
    }

    # Get layout
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    layout = get_active_or_new_layout()

    # For eigenmode simulations, we want a port across the islands
    if sim_tool == 'eigenmode':
        sim_parameters['internal_island_ports'] = False

    # Sweep simulations
    # simulations = [sim_class(layout, **sim_parameters)]
    simulations = sweep_simulation(layout, sim_class, sim_parameters, {
        'coupler_extent': [[float(w), 20.] for w in np.linspace(20, 400, 8, dtype=int)],
        'coupler_offset': [float(e) for e in np.linspace(5, 50, 5, dtype=int)],
        'ground_gap': [[float(w), float(h)] for w, h
            in product(np.linspace(550, 1000, 5, dtype=int), np.linspace(400, 1000, 5, dtype=int))],
        'squid_offset': [float(e) for e in np.linspace(-10, 0, 5, dtype=int)],
    })

    simulations += [sim_class(layout, **{
        **sim_parameters,
        **{
            'island1_extent': [float(i_w), float(i_h)],
            'island2_extent': [float(i_w), float(i_h)],
            'name': f'{sim_parameters["name"]}_island_extent_{i_w}_{i_h}'
        }
        })
        for i_w, i_h in zip(np.linspace(200, 600, 16, dtype=int), np.linspace(50, 200, 16, dtype=int))]

    simulations += [sim_class(layout, **{
        **sim_parameters,
        **{
            'island1_r': float(r),
            'island2_r': float(r),
            'name': f'{sim_parameters["name"]}_island_r_{r}'
        }
        })
        for r in np.linspace(0, 100, 8, dtype=int)]

    if sim_tool == 'elmer':
        export_elmer(simulations, dir_path, **export_parameters_elmer)
    else:
        export_ansys(simulations, **export_parameters_ansys)

logging.info(f'Total simulations: {len(simulations)}')
