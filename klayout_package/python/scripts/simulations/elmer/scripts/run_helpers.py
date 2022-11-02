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
import shutil
import subprocess
import sys
from pathlib import Path


def run_elmer_grid(msh_path, n_processes, exec_path_override=None):
    elmergrid_executable = shutil.which('ElmerGrid')
    if elmergrid_executable is not None:
        subprocess.check_call([elmergrid_executable, '14', '2', msh_path], cwd=exec_path_override)
        if n_processes > 1:
            subprocess.check_call([elmergrid_executable, '2', '2', Path(msh_path).stem + '/', '-metis',
                                   str(n_processes), '4', '-removeunused'], cwd=exec_path_override)
    else:
        logging.warning("ElmerGrid was not found! Make sure you have ElmerFEM installed: "
                        "https://github.com/ElmerCSC/elmerfem")
        sys.exit()


def run_elmer_solver(sif_path, n_processes, exec_path_override=None):
    elmersolver_executable = shutil.which('ElmerSolver')
    elmersolver_mpi_executable = shutil.which('ElmerSolver_mpi')
    if n_processes > 1 and elmersolver_mpi_executable is not None:
        mpi_command = 'mpirun' if shutil.which('mpirun') is not None else 'mpiexec'
        subprocess.check_call([mpi_command, '-np', str(n_processes), elmersolver_mpi_executable,
                               sif_path], cwd=exec_path_override)
    elif elmersolver_executable is not None:
        subprocess.check_call([elmersolver_executable, sif_path], cwd=exec_path_override)
    else:
        logging.warning("ElmerSolver was not found! Make sure you have ElmerFEM installed: "
                        "https://github.com/ElmerCSC/elmerfem")
        sys.exit()


def run_paraview(result_path, n_processes, exec_path_override=None):
    paraview_executable = shutil.which('paraview')
    if paraview_executable is not None:
        if n_processes > 1:
            subprocess.check_call([paraview_executable, '{}_t0001.pvtu'.format(result_path)], cwd=exec_path_override)
        else:
            subprocess.check_call([paraview_executable, '{}_t0001.vtu'.format(result_path)], cwd=exec_path_override)
    else:
        logging.warning("Paraview was not found! Make sure you have it installed: https://www.paraview.org/")
        sys.exit()
