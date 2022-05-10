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
import csv
import json
import shutil
from pathlib import Path


def export_elmer_sif(path: Path, msh_filepath: Path, port_data_gmsh: dict, ground_names: str, tool='capacitance'):
    """
    Exports an elmer simulation model to the simulation path.

    Args:

        path(Path): Location where to output the simulation model
        msh_filepath(Path): Path to exported msh file
        port_data_gmsh(list):

          each element contain port data that one gets from `Simulation.get_port_data` + gmsh specific data:

             * Items from `Simulation.get_port_data`
             * dim_tag: DimTags of the port polygons
             * occ_bounding_box: port bounding box
             * dim_tags: list of DimTags if the port consist of more than one (`EdgePort`)
             * signal_dim_tag: DimTag of the face that is connected to the signal edge of the port
             * signal_physical_name: physical name of the signal face

        ground_names(list): List of ground names in gmsh model
        tool(str): Elmer tool. Available: "capacitance" that computes the capacitance matrix (Default: capacitance)

    Returns:

        sif_filepath: Path to exported sif file

    """
    if tool == 'capacitance':
        sif_filepath = path.joinpath('sif/{}.sif'.format(msh_filepath.stem))
        begin = 'Check Keywords Warn\n'
        begin += 'INCLUDE {}/mesh.names\n'.format(msh_filepath.stem)
        begin += 'Header\n'
        begin += '  Mesh DB "." "{}"\n'.format(msh_filepath.stem)
        begin += 'End\n'

        n_ground = len(ground_names)
        s = 'Boundary Condition 1\n'
        s += '  Target Boundaries({}) = $ '.format(n_ground) + ' '.join(ground_names)
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
