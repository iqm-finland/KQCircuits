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
import logging
import shutil
import subprocess
from pathlib import Path
from sys import argv
import json
import csv

from kqcircuits.util.export_helper import write_commit_reference_file
from kqcircuits.defaults import ELMER_SCRIPTS_PATH
from kqcircuits.simulations.export.gmsh_helpers import export_gmsh_msh
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.util.geometry_json_encoder import GeometryJsonEncoder

def copy_elmer_scripts_to_directory(path: Path):
    """
    Copies Elmer scripts into directory path.

    Args:

        path: Location where to copy scripts folder.
    """
    if path.exists() and path.is_dir() and not path.joinpath("sif").exists():
        shutil.copytree(ELMER_SCRIPTS_PATH, path.joinpath('sif'))

def export_elmer_sif(simulation, msh_filepath: Path, port_data_gmsh: dict(), path: Path, tool='capacitance'):
    """
    Exports an elmer simulation model to the simulation path.

    Args:

        simulation(Simulation): Exported simulation
        msh_filepath(Path): Path to exported msh file
        port_data_gmsh(list):

          each element contain port data that one gets from `Simulation.get_port_data` + gmsh specific data:

             * Items from `Simulation.get_port_data`
             * dim_tag: DimTags of the port polygons
             * occ_bounding_box: port bounding box
             * dim_tags: list of DimTags if the port consist of more than one (`EdgePort`)
             * signal_dim_tag: DimTag of the face that is connected to the signal edge of the port
             * signal_physical_name: physical name of the signal face

        path(Path): Location where to output the simulation model
        tool(str): Elmer tool. Available: "capacitance" that computes the capacitance matrix (Default: capacitance)

    Returns:

        sif_filepath: Path to exported sif file

    """
    write_commit_reference_file(path)
    copy_elmer_scripts_to_directory(path)

    if tool == 'capacitance':
        sif_filepath = path.joinpath('sif/{}.sif'.format(msh_filepath.stem))
        begin = 'Check Keywords Warn\n'
        begin += 'INCLUDE {}/mesh.names\n'.format(msh_filepath.stem)
        begin += 'Header\n'
        begin += '  Mesh DB "." "{}"\n'.format(msh_filepath.stem)
        begin += 'End\n'

        n_ground = len(simulation.ground_names)
        s = 'Boundary Condition 1\n'
        s += '  Target Boundaries({}) = $ '.format(n_ground) + ' '.join(simulation.ground_names)
        s += '\n  Capacitance Body = 0\n'
        s += 'End\n'

        for i, port in enumerate([port for port in port_data_gmsh if 'signal_physical_name' in port]):
            s += 'Boundary Condition '+str(i+2)+'\n'
            s += '  Target Boundaries(1) = $ '+port['signal_physical_name']+'\n'
            s += '  Capacitance Body = '+str(i+1)+'\n'
            s += 'End\n'

        shutil.copy(path.joinpath('sif/CapacitanceMatrix.sif'), sif_filepath)
        with open(sif_filepath, 'r+') as f:
            content = f.read().replace('#FILEPATHSTEM', sif_filepath.stem)
            f.seek(0, 0)
            f.write(begin + content + s)

        with open(path.joinpath('ELMERSOLVER_STARTINFO'), 'w') as f:
            f.write(str(sif_filepath))

    return sif_filepath

def calculate_total_capacitance_to_ground(c_matrix):
    """Returns total capacitance to ground for each column of c_matrix."""
    columns = range(len(c_matrix))
    c_ground = []
    for i in columns:
        c_ground.append(
            c_matrix[i][i] + sum([c_matrix[i][j] / (1.0 + c_matrix[i][j] / c_matrix[j][j]) for j in columns if i != j]))
    return c_ground

def write_project_results_json(path: Path, msh_filepath):
    """
    Writes the solution data in '_project_results.json' format for one Elmer capacitance matrix computation.

    Args:
        path(Path): Location where to output the simulation model
        msh_filepath(Path): Location of msh file in `Path` format
    """
    c_matrix_filename = path.joinpath(msh_filepath.stem).joinpath('capacitancematrix.dat')
    json_filename = path.joinpath(msh_filepath.stem)
    json_filename = json_filename.parent / (json_filename.name + '_project_results.json')

    if c_matrix_filename.exists():

        with open(c_matrix_filename, 'r') as file:
            my_reader = csv.reader(file, delimiter=' ', skipinitialspace=True, quoting=csv.QUOTE_NONNUMERIC)
            c_matrix = [row[0:-1] for row in my_reader]

        c_data = {"C_Net{}_Net{}".format(net_i+1, net_j+1): [c_matrix[net_j][net_i]] for net_j in range(len(c_matrix))
                for net_i in range(len(c_matrix))}

        c_g = calculate_total_capacitance_to_ground(c_matrix)

        with open(json_filename, 'w') as outfile:
            json.dump({'CMatrix': c_matrix,
                       'Cg': c_g,
                       'Cdata': c_data,
                       'Frequency': [0],
                       }, outfile, indent=4)


def export_elmer_json(simulation: Simulation,
                      path: Path,
                      tool='capacitance',
                      ):
    """
    Export Ansys simulation into json and gds files.

    Arguments:
        simulation: The simulation to be exported.
        path: Location where to write json.
        tool(str): Elmer tool used. Available: "capacitance" that computes the capacitance matrix (Default: capacitance)

    Returns:
         Path to exported json file.
    """
    if simulation is None or not isinstance(simulation, Simulation):
        raise ValueError("Cannot export without simulation")

    simulation_data = simulation.get_simulation_data()
    simulation_data['tool'] = tool

    # write .json file
    json_filename = str(path.joinpath(simulation.name + '.json'))
    with open(json_filename, 'w') as fp:
        json.dump(simulation_data, fp, cls=GeometryJsonEncoder, indent=4)

    return json_filename


def export_elmer(simulations: [], path: Path, tool='capacitance',
                 default_mesh_size: float = 100,
                 signal_min_mesh_size: float = 100,
                 signal_max_mesh_size: float = 100,
                 signal_min_dist: float = 100,
                 signal_max_dist: float = 100,
                 signal_sampling: float = None,
                 ground_min_mesh_size: float = 100,
                 ground_max_mesh_size: float = 100,
                 ground_min_dist: float = 100,
                 ground_max_dist: float = 100,
                 ground_sampling: float = None,
                 ground_grid_min_mesh_size: float = 100,
                 ground_grid_max_mesh_size: float = 100,
                 ground_grid_min_dist: float = 100,
                 ground_grid_max_dist: float = 100,
                 ground_grid_sampling: float = None,
                 gap_min_mesh_size: float = 100,
                 gap_max_mesh_size: float = 100,
                 gap_min_dist: float = 100,
                 gap_max_dist: float = 100,
                 gap_sampling: float = None,
                 port_min_mesh_size: float = 100,
                 port_max_mesh_size: float = 100,
                 port_min_dist: float = 100,
                 port_max_dist: float = 100,
                 port_sampling: float = None,
                 algorithm: int = 5,
                 show: bool = False,
                 gmsh_n_threads: int = 1,
                 ):
    """
    Exports an elmer simulation model to the simulation path.

    Args:

        simulations(list(Simulation)): list of all the simulations
        path(Path): Location where to output the simulation model
        tool(str): Elmer tool used. Available: "capacitance" that computes the capacitance matrix (Default: capacitance)
        default_mesh_size(float): Default size to be used where not defined
        signal_min_mesh_size(float): Minimum mesh size near signal region curves
        signal_max_mesh_size(float): Maximum mesh size near signal region curves
        signal_min_dist(float): Mesh size will be the minimum size until this distance
                                from the signal region curves
        signal_max_dist(float): Mesh size will grow from to the maximum size until
                                this distance from the signal region curves
        signal_sampling(float): Number of points used for sampling each signal region curve
        ground_min_mesh_size(float): Minimum mesh size near ground region curves
        ground_max_mesh_size(float): Maximum mesh size near ground region curves
        ground_min_dist(float): Mesh size will be the minimum size until this distance
                                from the ground region curves
        ground_max_dist(float): Mesh size will grow from to the maximum size until
                                this distance from the ground region curves
        ground_sampling(float): Number of points used for sampling each ground region curve
        ground_grid_min_mesh_size(float): Minimum mesh size near ground_grid region curves
        ground_grid_max_mesh_size(float): Maximum mesh size near ground_grid region curves
        ground_grid_min_dist(float): Mesh size will be the minimum size until this distance
                                from the ground_grid region curves
        ground_grid_max_dist(float): Mesh size will grow from to the maximum size until
                                this distance from the ground_grid region curves
        ground_grid_sampling(float): Number of points used for sampling each ground_grid region curve
        gap_min_mesh_size(float): Minimum mesh size near gap region curves
        gap_max_mesh_size(float): Maximum mesh size near gap region curves
        gap_min_dist(float): Mesh size will be the minimum size until this distance
                                from the gap region curves
        gap_max_dist(float): Mesh size will grow from to the maximum size until
                                this distance from the gap region curves
        gap_sampling(float): Number of points used for sampling each gap region curve
        port_min_mesh_size(float): Minimum mesh size near port region curves
        port_max_mesh_size(float): Maximum mesh size near port region curves
        port_min_dist(float): Mesh size will be the minimum size until this distance
                                from the port region curves
        port_max_dist(float): Mesh size will grow from to the maximum size until
                                this distance from the port region curves
        port_sampling(float): Number of points used for sampling each port region curve
        algorithm(float): Gmsh meshing algorithm (default is 5)
        show(float): Show the mesh in Gmsh graphical interface after completing the mesh
                     (for large meshes this can take a long time)
        gmsh_n_threads(int): number of threads used in Gmsh meshing (default=1, -1 means all physical cores)

    Returns:

        msh_filepaths(list(Path)): List of locations of msh files in `Path` format
        sif_filepaths(list(Path)): List of locations of sif files in `Path` format
    """
    write_commit_reference_file(path)
    copy_elmer_scripts_to_directory(path)
    msh_filepaths = []
    sif_filepaths = []
    show = show and argv[-1] != "-q"
    for simulation in simulations:
        msh_filepath, port_data_gmsh = export_gmsh_msh(simulation, path,
                                                       default_mesh_size,
                                                       signal_min_mesh_size,
                                                       signal_max_mesh_size,
                                                       signal_min_dist,
                                                       signal_max_dist,
                                                       signal_sampling,
                                                       ground_min_mesh_size,
                                                       ground_max_mesh_size,
                                                       ground_min_dist,
                                                       ground_max_dist,
                                                       ground_sampling,
                                                       ground_grid_min_mesh_size,
                                                       ground_grid_max_mesh_size,
                                                       ground_grid_min_dist,
                                                       ground_grid_max_dist,
                                                       ground_grid_sampling,
                                                       gap_min_mesh_size,
                                                       gap_max_mesh_size,
                                                       gap_min_dist,
                                                       gap_max_dist,
                                                       gap_sampling,
                                                       port_min_mesh_size,
                                                       port_max_mesh_size,
                                                       port_min_dist,
                                                       port_max_dist,
                                                       port_sampling,
                                                       algorithm,
                                                       show,
                                                       gmsh_n_threads,
                                                       )
        sif_filepath = export_elmer_sif(simulation, msh_filepath, port_data_gmsh, path, tool)
        export_elmer_json(simulation, path, tool)
        msh_filepaths.append(msh_filepath)
        sif_filepaths.append(sif_filepath)

    return msh_filepaths, sif_filepaths


def run_elmer(path: Path, msh_filepaths: [],
              run_elmergrid=True, run_elmer=True, run_paraview=False,
              elmer_n_processes: int=1):
    """
    Run simulations using elmer.

    Args:
        path(Path): Location where to output the simulation model
        msh_filepaths(list(Path)): Locations of msh files in `Path` format
        run_elmergrid: if true, ElmerGrid is run (Default: True)
        run_elmer: if true, ElmerSolver is run (Default: True)
        run_paraview: if true, Paraview is launched at path (Default: False)
        elmer_n_processes(int): number of processes used in Elmer simulation (default=1, -1 means all physical cores)
    """
    if elmer_n_processes == -1:
        elmer_n_processes = int(os.cpu_count()/2 + 0.5)  # for the moment avoid psutil.cpu_count(logical=False)

    for msh_filepath in msh_filepaths:
        if run_elmergrid:

            if shutil.which('ElmerGrid') is not None:
                subprocess.check_call(['ElmerGrid', '14', '2', msh_filepath], cwd=path)
                if elmer_n_processes > 1:
                    subprocess.check_call(['ElmerGrid',
                       '2',
                       '2',
                       msh_filepath.stem,
                       '-metis',
                       '{}'.format(elmer_n_processes),
                       '4',
                       '-removeunused'],
                       cwd=path)
            else:
                logging.warning("ElmerGrid was not found! Make sure you have ElmerFEM "\
                        "installed: https://github.com/ElmerCSC/elmerfem")
                logging.warning("Mesh was created, but Elmer cannot be run!")
                return

        if run_elmer:
            if shutil.which('ElmerSolver') is not None:
                if elmer_n_processes > 1:
                    subprocess.check_call(['mpirun',
                        '-np',
                        '{}'.format(elmer_n_processes),
                        'ElmerSolver_mpi',
                        'sif/{}.sif'.format(msh_filepath.stem)],
                        cwd=path)
                else:
                    subprocess.check_call(['ElmerSolver', 'sif/{}.sif'.format(msh_filepath.stem)], cwd=path)

                write_project_results_json(path, msh_filepath)
            else:
                logging.warning("ElmerSolver was not found! Make sure you have ElmerFEM "\
                        "installed: https://github.com/ElmerCSC/elmerfem")
                logging.warning("Mesh was created, but Elmer cannot be run!")
                return

    if run_paraview and argv[-1] != "-q": # quiet mode, do not run viewer
        if shutil.which('paraview') is not None:
            subprocess.check_call(['paraview'], cwd=path)
        else:
            logging.warning("Paraview was not found! Make sure you have it "\
                    "installed: https://www.paraview.org/")
            logging.warning("The simulation was run, but Paraview cannot be run for viewing the results!")
            return
