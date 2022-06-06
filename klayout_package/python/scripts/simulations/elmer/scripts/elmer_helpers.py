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


def export_elmer_sif(path: Path, msh_filepath: Path, model_data: dict):
    """
    Exports an elmer simulation model to the simulation path.

    Args:

        path(Path): Location where to output the simulation model
        msh_filepath(Path): Path to exported msh file
        model_data(dict): Simulation model data including following terms:

            * 'tool': Elmer tool. Available: "capacitance" that computes the capacitance matrix,
            * 'faces': Number of faces,
            * 'port_signal_names': List of signal names in gmsh model for each port,
            * 'ground_names': List of ground names in gmsh model,
            * 'substrate_permittivity': Permittivity of the substrates,

    Returns:

        sif_filepath: Path to exported sif file

    """
    if model_data['tool'] == 'capacitance':
        sif_filepath = path.joinpath('sif/{}.sif'.format(msh_filepath.stem))
        begin = 'Check Keywords Warn\n'
        begin += 'INCLUDE {}/mesh.names\n'.format(msh_filepath.stem)
        begin += 'Header\n'
        begin += '  Mesh DB "." "{}"\n'.format(msh_filepath.stem)
        begin += 'End\n'

        # vacuum and substrates
        s = 'Body 1\n'
        s += '  Target Bodies(1) = $ vacuum\n'
        s += '  Equation = 1\n'
        s += '  Material = 1\n'
        s += 'End\n'
        for face in range(model_data['faces']):
            s += 'Body {}\n'.format(face + 2)
            s += '  Target Bodies(1) = $ chip_{}\n'.format(face)
            s += '  Equation = 1\n'
            s += '  Material = 2\n'
            s += 'End\n'

        # materials
        s += 'Material 1\n'
        s += '  Relative Permittivity = 1\n'
        s += 'End\n'
        s += 'Material 2\n'
        s += '  Relative Permittivity = {}\n'.format(model_data['substrate_permittivity'])
        s += 'End\n'

        # boundary conditions
        n_ground = len(model_data['ground_names'])
        s += 'Boundary Condition 1\n'
        s += '  Target Boundaries({}) = $ '.format(n_ground) + ' '.join(model_data['ground_names'])
        s += '\n  Capacitance Body = 0\n'
        s += 'End\n'

        for i, port_signal_name in enumerate(model_data['port_signal_names']):
            s += 'Boundary Condition '+str(i+2)+'\n'
            s += '  Target Boundaries(1) = $ '+port_signal_name+'\n'
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
