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
import os
import shutil
import subprocess
import sys
import json
from pathlib import Path
import argparse

from gmsh_helpers import export_gmsh_msh
from elmer_helpers import export_elmer_sif, write_project_results_json


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

args = parser.parse_args()

# Get input json filename as first argument
json_filename = args.json_filename
path = Path(os.path.split(json_filename)[0])

# Open json file
with open(json_filename) as f:
    json_data = json.load(f)
workflow = json_data['workflow']

if args.write_project_results:
    args.skip_gmsh = True
    args.skip_elmergrid = True
    args.skip_elmer = True
    args.skip_paraview = True

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
    json_data['gmsh_params']['show'] = False

# Generate mesh
if workflow['run_gmsh']:
    msh_filepath, model_data = export_gmsh_msh(json_data, path, **json_data['gmsh_params'])
    model_data['frequency'] = json_data['frequency']
    sif_filepath = export_elmer_sif(path, msh_filepath, model_data)
else:
    msh_filepath = path.joinpath(json_data['parameters']['name'] + '.msh')

# Set number of processes for elmer
elmer_n_processes = workflow['elmer_n_processes']
if elmer_n_processes == -1:
    elmer_n_processes = int(os.cpu_count()/2 + 0.5)  # for the moment avoid psutil.cpu_count(logical=False)

# Run ElmerGrid
if workflow['run_elmergrid']:
    if shutil.which('ElmerGrid') is not None:
        subprocess.check_call(['ElmerGrid', '14', '2', msh_filepath], cwd=path)
        if elmer_n_processes > 1:
            subprocess.check_call(['ElmerGrid', '2', '2', msh_filepath.stem + '/', '-metis',
                '{}'.format(elmer_n_processes), '4', '-removeunused'], cwd=path)
    else:
        logging.warning("ElmerGrid was not found! Make sure you have ElmerFEM " \
                        "installed: https://github.com/ElmerCSC/elmerfem")
        logging.warning("Mesh was created, but Elmer cannot be run!")
        sys.exit()

# Run Elmer simulation
if workflow['run_elmer']:
    if shutil.which('ElmerSolver') is not None:
        if elmer_n_processes > 1:
            mpi_command = 'mpirun' if shutil.which('mpirun') is not None else 'mpiexec'
            subprocess.check_call([mpi_command, '-np', '{}'.format(elmer_n_processes), 'ElmerSolver_mpi',
                                   'sif/{}.sif'.format(msh_filepath.stem)], cwd=path)
        else:
            subprocess.check_call(['ElmerSolver', 'sif/{}.sif'.format(msh_filepath.stem)], cwd=path)
        write_project_results_json(path, msh_filepath)
    else:
        logging.warning("ElmerSolver was not found! Make sure you have ElmerFEM installed: "
                        "https://github.com/ElmerCSC/elmerfem")
        logging.warning("Mesh was created, but Elmer cannot be run!")
        sys.exit()

# Run Paraview to view results
if workflow['run_paraview']:
    if shutil.which('paraview') is not None:
        if elmer_n_processes > 1:
            subprocess.check_call(['paraview', '{}/{}_t0001.pvtu'.format(msh_filepath.stem,
                msh_filepath.stem)], cwd=path)
        else:
            subprocess.check_call(['paraview', '{}/{}_t0001.vtu'.format(msh_filepath.stem,
                msh_filepath.stem)], cwd=path)
    else:
        logging.warning("Paraview was not found! Make sure you have it installed: https://www.paraview.org/")
        logging.warning("The simulation was run, but Paraview cannot be run for viewing the results!")
        sys.exit()

if args.write_project_results:
    write_project_results_json(path, msh_filepath)
