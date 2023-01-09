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

import numpy as np

from kqcircuits.simulations.double_pads_sim import DoublePadsSim
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.simulation_export import export_simulation_oas
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout, \
    open_with_klayout_or_default_application


sim_tools = ['elmer', 'eigenmode', 'q3d']

for sim_tool in sim_tools:
    # Simulation parameters
    sim_class = DoublePadsSim  # pylint: disable=invalid-name
    sim_parameters = {
        'name': 'double_pads',
        'use_internal_ports': True,
        'use_ports': True,
        'face_stack': ['1t1'],
        'box': pya.DBox(pya.DPoint(0, 0), pya.DPoint(2000, 2000)),

        'internal_island_ports': sim_tool != 'eigenmode'  # DoublePads specific
    }

    dir_path = create_or_empty_tmp_directory(Path(__file__).stem + f'_output_{sim_tool}')

    # Add eigenmode and Q3D specific settings
    export_parameters_ansys = {
        'percent_error': 0.3,
        'maximum_passes': 18,
        'minimum_passes': 2,
        'minimum_converged_passes': 2,
    } if sim_tool == 'q3d' else {
        'max_delta_f': 0.008,

        # do two passes with tight mesh
        'gap_max_element_length': 25,
        'maximum_passes': 17,
        'minimum_passes': 1,
        'minimum_converged_passes': 2,

        # lossy eigenmode simulation settings
        'n_modes': 1,
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

    export_parameters_ansys = {
        'ansys_tool': sim_tool,
        'path': dir_path,
        'exit_after_run': True,
        **export_parameters_ansys
    }

    export_parameters_elmer = {
        'tool': 'capacitance',
        'workflow': {
            'python_executable': 'python',
            'n_workers': 4,
            'elmer_n_processes': 4,
            'gmsh_n_threads': 4,
        },
        'mesh_size': {
            'global_max': 50.,
            'gap&signal': [2., 4.],
            'gap&ground': [2., 4.],
            'port': [1., 4.],
        }
    }

    # Get layout
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    layout = get_active_or_new_layout()

    # Sweep simulations
    # Here, we sweep coupler width with two different island-island gap widths:
    #   70 µm = 15.25 * 2 + 39.5
    #   150µm = 55.25 * 2 + 29.5
    # SIM junction set to 39.5 so that the gap between junction islands is same as that gap in Manhattan junction
    # Adapt taper widths to have 15 degree tapering angle from y-axis. Widths are different for each island
    # according to the Manhattan junction

    simulations = []
    for gap_height, junction_taper_width, island_width in zip([15.25, 55.25], [31, 31.7], [700, 775]):
        name = sim_parameters["name"]
        name = f'{name}_island_dist_{int(2*gap_height + 39.5)}'
        simulations += [sim_class(layout, **{
                **sim_parameters,
                'ground_gap': [900, 900],
                'coupler_extent': [round(coupler_width), 20],
                'island1_extent': [round(island_width), 200],
                'island2_extent': [round(island_width), 200],
                'junction_type': 'Manhattan',
                'junction_total_length': 39.5,
                'island1_taper_width': 2 * gap_height * np.tan(np.radians(15)) + 8,
                'island1_taper_height': gap_height,
                'island1_taper_junction_width': 8,
                'island2_taper_width': 2 * gap_height * np.tan(np.radians(15)) + junction_taper_width,
                'island2_taper_height': gap_height,
                'island2_taper_junction_width': junction_taper_width,
                'name': f'{name}_coupler_width_{round(coupler_width)}'
            })
            for coupler_width in np.linspace(50, 800, 21)
        ]

    # Create simulation
    oas = export_simulation_oas(simulations, dir_path)

    if sim_tool == 'elmer':
        export_elmer(simulations, dir_path, **export_parameters_elmer)
    else:
        export_ansys(simulations, **export_parameters_ansys)

logging.info(f'Total simulations: {len(simulations)}')
open_with_klayout_or_default_application(oas)
