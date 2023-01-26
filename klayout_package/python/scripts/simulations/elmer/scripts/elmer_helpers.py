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

def get_electrostatics_solver(method='mg', p_element_order=3):
    solver = 'Solver 1\n'
    solver += '\n'
    solver += '  Equation = Electro Statics\n'
    solver += '  Procedure = "StatElecSolveVec" "StatElecSolver"\n'
    solver += '  Variable = Potential\n'
    solver += '\n'
    solver += '  Calculate Capacitance Matrix = True\n'
    solver += '  Capacitance Matrix Filename = #FILEPATHSTEM/CapacitanceMatrix.dat\n'
    solver += '\n'
    solver += '  Nonlinear System Max Iterations = 1\n'
    solver += '  Nonlinear System Consistent Norm = True\n'
    solver += '\n'
    solver += '$pn={}\n'.format(p_element_order)
    solver += '\n'

    if method == 'bicgstab':
        solver += '  Linear System Solver = Iterative\n'
        solver += '  Linear System Iterative Method = BiCGStab\n'
        solver += '  Linear System Max Iterations = 200\n'
        solver += '  Linear System Convergence Tolerance = 1.0e-12\n'
        solver += '  Linear System Preconditioning = ILU1\n'
        solver += '  Linear System ILUT Tolerance = 1.0e-03\n'
    elif method == 'mg':
        solver += '! Outer iteration\n'
        solver += '  Linear System Solver = Iterative\n'
        solver += '  Linear System Iterative Method = GCR \n'
        solver += '  Linear System Max Iterations = 30\n'
        solver += '  Linear System Convergence Tolerance = 1.0e-12\n'
        solver += '  Linear System Abort Not Converged = False\n'
        solver += '  Linear System Residual Output = 10\n'
        solver += '\n'
        solver += '! You can edit here to compare to something more simple\n'
        solver += '  Linear System Preconditioning = multigrid !ILU2\n'
        solver += '  Linear System Refactorize = False\n'
        solver += '\n'
        solver += '! Settings for multigrid method\n'
        solver += '  MG Method = p\n'
        solver += '  MG Levels = $pn\n'
        solver += '  MG Smoother = SGS ! cg\n'
        solver += '  MG Pre Smoothing iterations = 2\n'
        solver += '  MG Post Smoothing Iterations = 2\n'
        solver += '  MG Lowest Linear Solver = iterative\n'
        solver += '\n'
        solver += '  mglowest: Linear System Scaling = False\n'
        solver += '  mglowest: Linear System Iterative Method = CG !BiCGStabl\n'
        solver += '  mglowest: Linear System Preconditioning = none !ILU0\n'
        solver += '  mglowest: Linear System Max Iterations = 100\n'
        solver += '  mglowest: Linear System Convergence Tolerance = 1.0e-4\n'

    solver += '\n'
    solver += '  Vector Assembly = True\n'
    solver += '  Element = p:$pn\n'
    solver += 'End\n'

    return solver

def export_elmer_sif(path: Path, msh_filepath: Path, model_data: dict):
    """
    Exports an elmer simulation model to the simulation path.

    Args:

        path(Path): Location where to output the simulation model
        msh_filepath(Path): Path to exported msh file
        model_data(dict): Simulation model data including following terms:

            * 'tool': Available: "capacitance" and "wave_equation" (Default: capacitance)
            * 'faces': Number of faces
            * 'port_signal_names': List of signal names in gmsh model for each port
            * 'ground_names': List of ground names in gmsh model
            * 'substrate_permittivity': Permittivity of the substrates
            * 'body_dim_tags': a list of dim_tags of the bodies in the model
            * 'body_materials': a dictionary mapping the bodies to their materials
            * 'body_port_phys_map': a dictionary mapping the bodies to the physical names of the port faces
            * 'frequency': the exitation frequency of the model

    Returns:

        sif_filepath: Path to exported sif file

    """
    sif_filepath = path.joinpath('sif/{}.sif'.format(msh_filepath.stem))
    begin = 'Check Keywords Warn\n'
    begin += 'INCLUDE "{}/mesh.names"\n'.format(msh_filepath.stem)
    begin += 'Header\n'
    begin += '  Mesh DB "." "{}"\n'.format(msh_filepath.stem)
    begin += 'End\n'

    # vacuum and substrates
    n_bodies = 0
    n_boundaries = 0
    s = 'Body 1\n'
    s += '  Target Bodies(1) = $ vacuum\n'
    s += '  Equation = 1\n'
    s += '  Material = 1\n'
    s += 'End\n'
    n_bodies += 1
    for face in range(model_data['faces']):
        s += 'Body {}\n'.format(face + 2)
        s += '  Target Bodies(1) = $ chip_{}\n'.format(face)
        s += '  Equation = 1\n'
        s += '  Material = 2\n'
        s += 'End\n'
        n_bodies += 1

    # materials
    s += 'Material 1\n'
    s += '  Relative Permittivity = 1\n'
    s += 'End\n'
    s += 'Material 2\n'
    s += '  Relative Permittivity = {}\n'.format(model_data['substrate_permittivity'])
    s += 'End\n'

    if model_data['tool'] == 'capacitance':
        # boundary conditions
        n_ground = len(model_data['ground_names'])
        s += 'Boundary Condition 1\n'
        s += '  Target Boundaries({}) = $ '.format(n_ground) + ' '.join(model_data['ground_names'])
        s += '\n  Potential = 0.0\n'
        s += 'End\n'
        n_boundaries += 1

        for i, port_signal_name in enumerate(model_data['port_signal_names']):
            s += 'Boundary Condition '+str(i+2)+'\n'
            s += '  Target Boundaries(1) = $ '+port_signal_name+'\n'
            s += '  Capacitance Body = '+str(i+1)+'\n'
            s += 'End\n'
            n_boundaries += 1

        shutil.copy(path.joinpath('sif/CapacitanceMatrix.sif'), sif_filepath)
        with open(sif_filepath, 'r+') as f:
            exec_output = "Always"
            content = replace_strings(f.read(),
                    {
                        '#SOLVER1': get_electrostatics_solver(method=model_data['linear_system_method'],
                                                              p_element_order=model_data['p_element_order']),
                        '#FILEPATHSTEM': sif_filepath.stem,
                        '#EXEC_RESULTOUTPUT': exec_output,
                    }
                    )
            f.seek(0, 0)
            f.write(begin + content + s)

        with open(path.joinpath('ELMERSOLVER_STARTINFO'), 'w') as f:
            f.write(str(sif_filepath))

    elif model_data['tool'] == 'wave_equation':
        # boundary conditions
        n_ground = len(model_data['ground_names'])
        s += 'Boundary Condition 1\n'
        s += '  Target Boundaries({}) = $ '.format(n_ground) + ' '.join(model_data['ground_names'])
        s += '\n  E re {e} = 0\n'
        s += '  E im {e} = 0\n'
        s += '  Potential = 0\n'
        s += 'End\n'
        n_boundaries += 1

        for i, port_signal_name in enumerate(model_data['port_signal_names']):
            s += 'Boundary Condition '+str(i+2)+'\n'
            s += '  Target Boundaries(1) = $ '+port_signal_name+'\n'
            s += '\n  E re {e} = 0\n'
            s += '  E im {e} = 0\n'
            s += '  Potential = 1\n'
            s += 'End\n'
            n_boundaries += 1

        for i, body_dim_tag in enumerate(model_data['body_dim_tags']):
            body_id = i+1+n_bodies
            s += 'Body {}\n'.format(body_id)
            # s += '  Target Bodies(1) = {}\n'.format(body_dim_tag[1])
            s += '  Equation = 2\n'
            if model_data['body_materials'][body_dim_tag] == 'vacuum':
                s += '  Material = 1\n'
            else:
                s += '  Material = 2\n'
            s += 'End\n'

            boundary_physical_names = model_data['body_port_phys_map'][body_dim_tag]
            s += 'Boundary Condition {}'.format(i+1+n_boundaries)+'\n'
            s += '  Target Boundaries({}) = $ '.format(len(boundary_physical_names)) + \
                                            ' '.join(boundary_physical_names)+'\n'
            s += '\n  Body Id = {}\n'.format(body_id)
            s += '  TEM Potential im = variable potential\n'
            s += '    real matc "2*beta*tx"\n'
            s += '  electric robin coefficient im = real $ beta\n'
            s += 'End\n'

        shutil.copy(path.joinpath('sif/WaveEquation.sif'), sif_filepath)
        with open(sif_filepath, 'r+') as f:
            content = f.read().replace('#FREQUENCY', str(1e9*model_data['frequency']))
            content = content.replace('#SUBSTRATE_PERMITTIVITY', str(model_data['substrate_permittivity']))
            content = content.replace('#FILEPATHSTEM', sif_filepath.stem)
            f.seek(0, 0)
            f.write(begin + content + s)

        with open(path.joinpath('ELMERSOLVER_STARTINFO'), 'w') as f:
            f.write(str(sif_filepath))

    return sif_filepath

def replace_strings(content, replace_dict):
    for key in replace_dict.keys():
        content = content.replace(key, replace_dict[key])
    return content

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

        with open(json_filename, 'w') as outfile:
            json.dump({'CMatrix': c_matrix,
                       'Cdata': c_data,
                       'Frequency': [0],
                       }, outfile, indent=4)
