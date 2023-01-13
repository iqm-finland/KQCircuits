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
import os
import json
from pathlib import Path
import argparse

from gmsh_helpers import export_gmsh_msh
from elmer_helpers import export_elmer_sif, write_project_results_json
from run_helpers import run_elmer_grid, run_elmer_solver, run_paraview, write_simulation_machine_versions_file
from cross_section_helpers import produce_cross_section_mesh, produce_cross_section_sif_files, \
    get_cross_section_capacitance_and_inductance, get_interface_quality_factors

parser = argparse.ArgumentParser(description='Run script for Gmsh-Elmer workflow')
parser.add_argument('json_filename', type=str, help='KQC simulation data')
parser.add_argument('--skip-gmsh', action='store_true', help="Run everything else but Gmsh")
parser.add_argument('--skip-elmergrid', action='store_true', help="Run everything else but Elmergrid")
parser.add_argument('--skip-elmer', action='store_true', help="Run everything else but Elmer")
parser.add_argument('--skip-paraview', action='store_true', help="Run everything else but Paraview")

parser.add_argument('--only-gmsh', action='store_true', help="Run only Gmsh")
parser.add_argument('--only-elmergrid', action='store_true', help="Run only Elmergrid")
parser.add_argument('--only-elmer', action='store_true', help="Run only Elmer")
parser.add_argument('--only-paraview', action='store_true', help="Run only Paraview")

parser.add_argument('-q', action='store_true', help="Quiet operation: no GUIs are launched")

parser.add_argument('--write-project-results', action='store_true',
        help="Write the results in KQC 'project.json' -format")

parser.add_argument('--write-versions-file', action='store_true',
        help="Write the versions of used software in 'SIMULATION_MACHINE_VERSIONS.json'")

args = parser.parse_args()

# Get input json filename as first argument
json_filename = args.json_filename
path = Path(json_filename).parent
name = Path(Path(json_filename).stem)

# Open json file
with open(json_filename) as f:
    json_data = json.load(f)
workflow = json_data['workflow']

if args.write_project_results:
    args.skip_gmsh = True
    args.skip_elmergrid = True
    args.skip_elmer = True
    args.skip_paraview = True

if args.write_versions_file:
    args.skip_gmsh = True
    args.skip_elmergrid = True
    args.skip_elmer = True
    args.skip_paraview = True
    args.write_project_results = False

if args.only_gmsh:
    args.skip_elmergrid = True
    args.skip_elmer = True
    args.skip_paraview = True
elif args.only_elmergrid:
    args.skip_gmsh = True
    args.skip_elmer = True
    args.skip_paraview = True
elif args.only_elmer:
    args.skip_gmsh = True
    args.skip_elmergrid = True
    args.skip_paraview = True
elif args.only_paraview:
    args.skip_gmsh = True
    args.skip_elmergrid = True
    args.skip_elmer = True

if args.skip_gmsh:
    workflow['run_gmsh'] = False
if args.skip_elmergrid:
    workflow['run_elmergrid'] = False
if args.skip_elmer:
    workflow['run_elmer'] = False
if args.skip_paraview:
    workflow['run_paraview'] = False

if args.q:
    workflow['run_paraview'] = False
    workflow['run_gmsh_gui'] = False

# Set number of processes for elmer
elmer_n_processes = workflow.get('elmer_n_processes', 1)
if elmer_n_processes == -1:
    elmer_n_processes = int(os.cpu_count()/2 + 0.5)  # for the moment avoid psutil.cpu_count(logical=False)

tool = json_data.get('tool', 'capacitance')
if tool == 'cross-section':
    # Generate mesh
    msh_file = f'{name}.msh'
    if workflow.get('run_gmsh', True):
        produce_cross_section_mesh(json_data, path.joinpath(msh_file))

    # Run sub-processes
    if workflow.get('run_elmergrid', True):
        run_elmer_grid(msh_file, elmer_n_processes, path)
    if workflow.get('run_elmer', True):
        # TODO: here we should also use p-elements and the vectorized Elmer
        sif_files = produce_cross_section_sif_files(json_data, path.joinpath(name))
        for sif_file in sif_files:
            run_elmer_solver(name.joinpath(sif_file), elmer_n_processes, path)
        res = get_cross_section_capacitance_and_inductance(json_data, path.joinpath(name))
        if 'dielectric_surfaces' in json_data:  # Compute quality factors with energy participation ratio method
            res = {**res, **get_interface_quality_factors(json_data, path.joinpath(name))}
        with open(path.joinpath(f'{name}_result.json'), 'w') as f:
            json.dump(res, f, indent=4)
    if workflow.get('run_paraview', False):
        run_paraview(name.joinpath('capacitance'), elmer_n_processes, path)


else:
    # Generate mesh
    if workflow.get('run_gmsh', True):
        params = {}
        if 'run_gmsh_gui' in workflow:
            params['show'] = workflow['run_gmsh_gui']
        if 'gmsh_n_threads' in workflow:
            params['gmsh_n_threads'] = workflow['gmsh_n_threads']
        msh_filepath, model_data = export_gmsh_msh(json_data, path, json_data['mesh_size'], **params)
        model_data['frequency'] = json_data['frequency']
        model_data['linear_system_method'] = json_data['linear_system_method']
        model_data['p_element_order'] = json_data['p_element_order']
        sif_filepath = export_elmer_sif(path, msh_filepath, model_data)
    else:
        msh_filepath = path.joinpath(json_data['parameters']['name'] + '.msh')

    # Set number of processes for elmer
    elmer_n_processes = workflow.get('elmer_n_processes', 1)
    if elmer_n_processes == -1:
        elmer_n_processes = int(os.cpu_count()/2 + 0.5)  # for the moment avoid psutil.cpu_count(logical=False)

    # Run sub-processes
    if workflow.get('run_elmergrid', True):
        run_elmer_grid(msh_filepath, elmer_n_processes, path)
    if workflow.get('run_elmer', True):
        run_elmer_solver(f'sif/{msh_filepath.stem}.sif', elmer_n_processes, path)
    if workflow.get('run_paraview', False):
        run_paraview(f'{msh_filepath.stem}/{msh_filepath.stem}', elmer_n_processes, path)

    # Write result file
    if args.write_project_results:
        write_project_results_json(path, msh_filepath)
    elif args.write_versions_file:
        write_simulation_machine_versions_file(path, json_data['parameters']['name'])
