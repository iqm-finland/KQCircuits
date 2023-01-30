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

import re
import os
from pathlib import Path

import numpy as np
import pandas as pd
import gmsh
from scipy.constants import mu_0, epsilon_0

from gmsh_helpers import separated_hull_and_holes, add_polygon, set_mesh_size_field, get_recursive_children, \
    set_meshing_options

try:
    import pya
except ImportError:
    import klayout.db as pya

angular_frequency = 5e9  # a constant for inductance simulations (technically is needed but doesn't affect results)


def produce_cross_section_mesh(json_data, msh_file):
    """Produces mesh and optionally runs the Gmsh GUI"""
    # Initialize gmsh
    gmsh.initialize()

    # Read geometry from gds file
    layout = pya.Layout()
    layout.read(json_data['gds_file'])
    cell = layout.top_cell()

    # Limiting boundary box (use variable 'box' if it is given. Otherwise, use bounding bo of the geometry.)
    if 'box' in json_data:
        bbox = pya.DBox(pya.DPoint(*json_data['box'][0]), pya.DPoint(*json_data['box'][1])).to_itype(layout.dbu)
    else:
        bbox = cell.bbox()

    # Create vacuum layer if it doesn't exist
    layers = json_data['layers']
    if 'vacuum' not in layers:
        vacuum = pya.Region(bbox)
        for n in layers.values():
            vacuum -= pya.Region(cell.shapes(layout.layer(*n)))
        # find free slot for vacuum layer
        layers['vacuum'] = next([n, 0] for n in range(1000) if [n, 0] not in layers.values())
        cell.shapes(layout.layer(*layers['vacuum'])).insert(vacuum)

    # Create mesh using geometries in gds file
    gmsh.model.add("cross_section")
    dim_tags = {}
    for name, num in layers.items():
        reg = pya.Region(cell.shapes(layout.layer(*num))) & bbox
        layer_dim_tags = []
        for simple_poly in reg.each():
            poly = separated_hull_and_holes(simple_poly)
            hull_point_coordinates = [
                (point.x * layout.dbu, point.y * layout.dbu, 0) for point in poly.each_point_hull()
            ]
            hull_plane_surface_id = add_polygon(hull_point_coordinates)
            hull_dim_tag = (2, hull_plane_surface_id)
            hole_dim_tags = []
            for hole in range(poly.holes()):
                hole_point_coordinates = [
                    (point.x * layout.dbu, point.y * layout.dbu, 0) for point in poly.each_point_hole(hole)
                ]
                hole_plane_surface_id = add_polygon(hole_point_coordinates)
                hole_dim_tags.append((2, hole_plane_surface_id))
            if hole_dim_tags:
                layer_dim_tags += gmsh.model.occ.cut([hull_dim_tag], hole_dim_tags)[0]
            else:
                layer_dim_tags.append(hull_dim_tag)
        dim_tags[name] = layer_dim_tags

    # Call fragment and get updated dim_tags as new_tags. Then synchronize.
    all_dim_tags = [tag for tags in dim_tags.values() for tag in tags]
    _, dim_tags_map_imp = gmsh.model.occ.fragment(all_dim_tags, [], removeTool=False)
    dim_tags_map = dict(zip(all_dim_tags, dim_tags_map_imp))
    new_tags = {
        name: [new_tag for old_tag in tags for new_tag in dim_tags_map[old_tag]]
        for name, tags in dim_tags.items()
    }
    gmsh.model.occ.synchronize()

    # Refine mesh
    # Here json_data['mesh_size'] is assumed to be dictionary where key denotes material (string) and value (double)
    # denotes the maximal length of mesh element. Additional terms can be determined, if the value type is list. Then,
    # - term[0] = the maximal mesh element length inside at the entity and its expansion
    # - term[1] = expansion distance in which the maximal mesh element length is constant (default=term[0])
    # - term[2] = the slope of the increase in the maximal mesh element length outside the entity
    #
    # To refine material interface the material names by should be separated by '&' in the key. Key 'global_max' is
    # reserved for setting global maximal element length. For example, if the dictionary is given as
    # {'substrate': 10, 'substrate&vacuum': [2, 5], 'global_max': 100}, then the maximal mesh element length is 10
    # inside the substrate and 2 on region which is less than 5 units away from the substrate-vacuum interface. Outside
    # these regions, the mesh element size can increase up to 100.
    mesh_size = json_data.get('mesh_size', {})
    mesh_global_max_size = mesh_size.pop('global_max', bbox.perimeter())
    mesh_field_ids = []
    for name, size in mesh_size.items():
        intersection = set()
        for sname in name.split('&'):
            if sname in new_tags:
                family = get_recursive_children(new_tags[sname]).union(new_tags[sname])
                intersection = intersection.intersection(family) if intersection else family

        mesh_field_ids += set_mesh_size_field(list(intersection - get_recursive_children(intersection)),
                                              mesh_global_max_size, *(size if isinstance(size, list) else [size]))

    # Set meshing options
    workflow = json_data.get('workflow', dict())
    gmsh_n_threads = workflow.get('gmsh_n_threads', 1)
    if gmsh_n_threads == -1:
        gmsh_n_threads = int(os.cpu_count() / 2 + 0.5)  # for the moment avoid psutil.cpu_count(logical=False)
    set_meshing_options(mesh_field_ids, mesh_global_max_size, gmsh_n_threads)

    # Add physical groups
    for n in new_tags:
        gmsh.model.addPhysicalGroup(2, [t[1] for t in new_tags[n]], name=n)
    metals = [n for n in new_tags if 'signal' in n or 'ground' in n]
    for n in metals:
        metal_boundary = gmsh.model.getBoundary(new_tags[n], combined=False, oriented=False, recursive=False)
        gmsh.model.addPhysicalGroup(1, [t[1] for t in metal_boundary], name=f'{n}_boundary')

    # Generate and save mesh
    gmsh.model.mesh.generate(2)
    gmsh.write(str(msh_file))

    # Open mesh viewer
    if workflow.get('run_gmsh_gui', False):
        gmsh.fltk.run()

    gmsh.finalize()


def coordinate_scaling(json_data):
    """Returns coordinate scaling, which is determined by parameters 'units' in json_data."""
    units = json_data.get('units', '').lower()
    return {'nm': 1e-9, 'um': 1e-6, 'µm': 1e-6, 'mm': 1e-3}.get(units, 1.0)


def sif_block(block_name, data):
    """Returns block segment of sif file in string format. Argument data is list of lines inside the block.
    The block is of shape:

    'block_name'
      data[0]
      data[1]
      .
      .
    End
    """
    res = block_name + '\n'
    for line in data:
        res += f'  {line}\n'
    res += 'End\n'
    return res


def sif_common_header(json_data, folder_path, def_file=None):
    """Returns common header and simulation blocks of a sif file in string format.
    Optional definition file name is given in 'def_file'."""
    res = 'Check Keywords Warn\n'
    res += 'INCLUDE {}/{}\n'.format(folder_path, 'mesh.names')
    if def_file:
        res += 'INCLUDE {}/{}\n'.format(folder_path, def_file)
    res += sif_block('Header', [
        'Mesh DB "." "{}"'.format(folder_path)])
    res += sif_block('Simulation', [
        'Max Output Level = 3',
        ('Coordinate System = "Axi Symmetric"' if json_data.get('is_axisymmetric', False)
         else 'Coordinate System = "Cartesian 2D"'),
        'Simulation Type = "Steady State"',
        'Steady State Max Iterations = 1',
        'Angular Frequency = {}'.format(angular_frequency),
        'Coordinate Scaling = {}'.format(coordinate_scaling(json_data))])
    return res


def sif_capacitance(json_data, folder_path, with_zero=False):
    """Returns capacitance sif file content in string format."""
    name = 'capacitance0' if with_zero else 'capacitance'
    res = sif_common_header(json_data, folder_path)
    res += sif_block('Constants', [f'Permittivity Of Vacuum = {epsilon_0}'])
    res += sif_block('Equation 1', [
        'Active Solvers(2) = 1 2',
        'Calculate Electric Energy = True'])
    solver_1_common_terms = [
        'Equation = Stat Elec Solver',
        'Variable = Potential',
        'Variable DOFs = 1',
        'Procedure = "StatElecSolveVec" "StatElecSolver"',
        'Calculate Elemental Fields = Logical True',
        'Calculate Electric Field = True',
        'Calculate Electric Flux = False',
        'Calculate Capacitance Matrix = True',
        'Capacitance Matrix Filename = {}/{}'.format(folder_path, name + '.dat'),
        'Linear System Solver = Iterative',
        'Nonlinear System Max Iterations = 1',
        '$pn={p_element_order}'.format(**json_data),
        'Vector Assembly = Logical True',
        'Element = p:$pn',
    ]
    if json_data.get('linear_system_method', None) == 'bicgstab':
        res += sif_block('Solver 1', solver_1_common_terms + [
            'Linear System Iterative Method = BiCGStabL',
            'Linear System Max Iterations = 1000',
            'Linear System Convergence Tolerance = 1.0e-10',
            'BiCGStabl polynomial degree = 2',
            'Linear System Preconditioning = ILU0',
            'Linear System ILUT Tolerance = 1.0e-03',

            'Nonlinear System Convergence Tolerance = 1.0e-4',
            'Nonlinear System Newton After Tolerance = 1.0e-3',
            'Nonlinear System Newton After Iterations = 10',
            'Nonlinear System Relaxation Factor = 1',

            'Steady State Convergence Tolerance = 1.0e-4',
        ])
    else:  # multigrid
        res += sif_block('Solver 1', solver_1_common_terms + [
            'Optimize Bandwidth = True',
            'Linear System Iterative Method = GCR',
            'Linear System Max Iterations = 100',
            'Linear System Convergence Tolerance = 1.0e-09',
            'Linear System Abort Not Converged = False',
            'Linear System Residual Output = 10',
            'Linear System Preconditioning = multigrid !ILU2',
            'Linear System Refactorize = False',

            'Nonlinear System Consistent Norm = True',

            '! Settings for multigrid method',
            'MG Method = p',
            'MG Levels = $pn',
            'MG Smoother = SGS ! cg',
            'MG Pre Smoothing iterations = 2',
            'MG Post Smoothing Iterations = 2',
            'MG Lowest Linear Solver = iterative',
            'mglowest: Linear System Scaling = False',
            'mglowest: Linear System Iterative Method = BiCGStabl !CG',
            'mglowest: Linear System Preconditioning = none !ILU0',
            'mglowest: Linear System Max Iterations = 100',
            'mglowest: Linear System Convergence Tolerance = 1.0e-3',
        ])

    res += sif_block('Solver 2', [
        'Exec Solver = True',
        'Equation = "ResultOutput"',
        'Procedure = "ResultOutputSolve" "ResultOutputSolver"',
        'Output File Name = {}'.format(name),
        'Vtu format = Logical True',
        'Discontinuous Bodies = Logical True',
        'Save Geometry Ids = Logical True'])
    res += sif_block('Solver 3', [
        'Exec Solver = Always',
        'Equation = "sv"',
        'Procedure = "SaveData" "SaveScalars"',
        'Filename = results.dat'])

    # Divide layers into different materials
    solids = list(set(json_data['layers'].keys()) | {'vacuum'})
    permittivities = [1.0 if with_zero else json_data.get(f'{s}_permittivity', 1.0) for s in solids]

    if 'dielectric_surfaces' in json_data and not with_zero:  # no EPR for kinetic inductance
        res += sif_block('Solver 4', [
            'Exec Solver = Always',
            'Equation = "SaveEnergy"',
            'Procedure = "SaveData" "SaveScalars"',
            f'Filename = {folder_path}/energy.dat',
            'Parallel Reduce = Logical True',
            # Add all target bodies to the solver
            *(line for layer_props in ((
                f'Variable {i} = Potential',
                f'Operator {i} = body diffusive energy',
                f'Mask Name {i} = {interface}',
                f'Coefficient {i} = Relative Permittivity'
                ) for i, interface in enumerate(solids, 1)
            ) for line in layer_props)
        ])

    # Write bodies and materials
    for i, (solid, perm) in enumerate(zip(solids, permittivities), 1):
        res += sif_block(f'Body {i}', [
            f'Target Bodies(1) = $ {solid}',
            'Equation = 1',
            f'Material = {i}',
            f'{solid} = Logical True',
        ])
        res += sif_block(f'Material {i}', [
            f'Relative Permittivity = {perm}',
        ])

    # Write metal boundary conditions
    signals = [n for n in json_data['layers'].keys() if 'signal' in n]
    grounds = [n for n in json_data['layers'].keys() if 'ground' in n and n not in signals]
    res += sif_block('Boundary Condition 1', [
        'Target Boundaries({}) = $ {}'.format(len(grounds), ' '.join(['{}_boundary'.format(s) for s in grounds])),
        'Potential = 0.0',
    ])
    for i, s in enumerate(signals, 1):
        res += sif_block(f'Boundary Condition {i+1}', [
            f'Target Boundaries(1) = $ {s}_boundary',
            f'Capacitance Body = {i}',
        ])
    return res


def sif_inductance(json_data, folder_path, def_file):
    """Returns inductance sif file content in string format."""
    res = sif_common_header(json_data, folder_path, def_file)
    res += sif_block('Equation 1', [
        'Active Solvers(3) = 1 2 3'])
    res += sif_block('Solver 1', [
        'Exec Solver = Always',
        'Equation = Circuits',
        'Variable = X',
        'No Matrix = Logical True',
        'Procedure = "CircuitsAndDynamics" "CircuitsAndDynamicsHarmonic"'])
    res += sif_block('Solver 2', [
        'Equation = "Mag"',
        'Variable = A[A re:1 A im:1]',
        'Procedure = "MagnetoDynamics2D" "MagnetoDynamics2DHarmonic"',
        'Linear System Symmetric = True',
        'NonLinear System Relaxation Factor = 1',
        'Export Lagrange Multiplier = Logical True',
        'Linear System Solver = "Direct"',
        'Linear System Iterative Method = BicgStabL',
        'Linear System Preconditioning = None',
        'Linear System Complex = Logical True',
        'Linear System Convergence Tolerance = 1.e-7',
        'Linear System Max Iterations = 3000',
        'Linear System Residual Output = 10',
        'Linear System Abort not Converged = False',
        'Linear System ILUT Tolerance=1e-8',
        'BicgStabL Polynomial Degree = 6',
        'Steady State Convergence Tolerance = 1e-06'])
    res += sif_block('Solver 3', [
        'Exec Solver = Always',
        'Equation = "MGDynamicsCalc"',
        'Procedure = "MagnetoDynamics" "MagnetoDynamicsCalcFields"',
        'Linear System Symmetric = True',
        'Potential Variable = String "A"',
        'Calculate Current Density = Logical True',
        'Calculate Magnetic Vector Potential = Logical True',
        'Steady State Convergence Tolerance = 0',
        'Linear System Solver = "Direct"',
        'Linear System Preconditioning = None',
        'Linear System Residual Output = 0',
        'Linear System Max Iterations = 5000',
        'Linear System Iterative Method = CG',
        'Linear System Convergence Tolerance = 1.0e-8'])
    res += sif_block('Solver 4', [
        'Exec Solver = Always',
        'Equation = "ResultOutput"',
        'Procedure = "ResultOutputSolve" "ResultOutputSolver"',
        'Output File Name = inductance',
        'Vtu format = Logical True',
        'Save Geometry Ids = Logical True'])
    res += sif_block('Solver 5', [
        'Exec Solver = Always',
        'Equation = Circuits Output',
        'Procedure = "CircuitsAndDynamics" "CircuitsOutput"'])
    res += sif_block('Solver 6', [
        'Exec Solver = Always',
        'Equation = "sv"',
        'Procedure = "SaveData" "SaveScalars"',
        'Filename = {}/{}'.format(folder_path, 'inductance.dat')])

    # Divide layers into different materials
    signals = [n for n in json_data['layers'].keys() if 'signal' in n]
    grounds = [n for n in json_data['layers'].keys() if 'ground' in n and n not in signals]
    solids = ['vacuum', *[n for n in json_data['layers'].keys() if n not in signals + grounds and n != 'vacuum']]

    res += sif_block('Body 1', [
        'Target Bodies({}) = $ {}'.format(len(solids), ' '.join(solids)),
        'Equation = 1',
        'Material = 1'])
    res += sif_block('Material 1', [
        'Relative Permeability = 1',
        'Electric Conductivity = 1'])

    res += sif_block('Body 2', [
        'Target Bodies({}) = $ {}'.format(len(grounds), ' '.join(grounds)),
        'Equation = 1',
        'Material = 2'])
    res += sif_block('Body 3', [
        'Target Bodies({}) = $ {}'.format(len(signals), ' '.join(signals)),
        'Equation = 1',
        'Material = 2'])
    london_penetration_depth = json_data.get('london_penetration_depth', 0.0)
    if london_penetration_depth > 0:
        opt_params = ['Electric Conductivity = 0',
                      '$ lambda_l = {}'.format(london_penetration_depth),
                      '$ mu_0 = 4e-7*pi',
                      'London Lambda = Real $ mu_0 * lambda_l^2']
    else:
        opt_params = ['Electric Conductivity = 1e10']
    res += sif_block('Material 2', [
        'Relative Permeability = 1',
        *opt_params])

    london_param = ['London Equations = Logical True'] if london_penetration_depth > 0 else []
    res += sif_block('Component 1', [
        'Name = String test inductor',
        'Master Bodies = Integer 3',
        'Coil Type = String Massive',
        *london_param])
    res += sif_block('Body Force 1', [
        'Name = "Circuit"',
        'testsource Re = Real 1.0',
        'testsource Im = Real 0.0'])
    return res


def sif_inductance_definitions(json_data):
    """Returns content of inductance definitions file in string format."""
    res = '$ Circuits = 1\n'

    # Define variable count and initialize circuit matrices.
    london_penetration_depth = json_data.get('london_penetration_depth', 0.0)
    n_equations = 4 + int(london_penetration_depth > 0.0)
    res += f'\n$ C.1.perm = zeros({n_equations})\n'
    for i in range(n_equations):
        res += f'$ C.1.perm({i % (n_equations - 1) + 1 if i > 0 and n_equations == 4 else i}) = {i}\n'

    res += f'\n$ C.1.variables = {n_equations}\n'
    for n in ['A', 'B', 'Mre', 'Mim']:
        res += '$ C.1.{} = zeros({n_equations},{n_equations})\n'.format(n, n_equations=n_equations)

    # Define variables
    res += '\n'
    var_names = ['i_testsource', 'v_testsource', 'i_component(1)', 'v_component(1)']
    if london_penetration_depth > 0.0:
        # If London equations are activated, phi_component(1) takes the role and place of v_component(1).
        # Then v_component(1) becomes nothing but a conventional circuit variable and the user has to write d_t phi = v,
        # if he wishes to drive the SC with voltage.
        var_names.insert(3, 'phi_component(1)')
    for i, var_name in enumerate(var_names):
        res += f'$ C.1.name.{i + 1} = "{var_name}"\n'

    # 1st equation
    res += f'\n$ C.1.B(0,{n_equations - 4}) = 1\n'
    res += '$ C.1.source.1 = "testsource"\n'

    # 2nd equation: Voltage relations (v_testsource + v_component(1) = 0)
    res += '\n$ C.1.B(1,1) = 1\n'
    res += f'$ C.1.B(1,{n_equations - 1}) = 1\n'

    # 3rd equation: Current relations (i_testsource - i_component(1) = 0)
    res += '\n$ C.1.B(2,0) = 1\n'
    res += '$ C.1.B(2,2) = -1\n'

    # 4th equation: (d_t phi_component(1) - v_component(1) = 0)
    if london_penetration_depth > 0.0:
        res += '\n$ C.1.A(4,3) = 1\n'
        res += '$ C.1.B(4,4) = -1\n'

    # 1 component equation, linking phi and i of the component 1, written by elmer at the row 4
    # (beta a, phi') + phi_component(1) (beta grad phi_0, grad phi') = i_component(1)
    return res


def produce_cross_section_sif_files(json_data, folder_path):
    """Produces sif files required for capacitance and inductance simulations. Returns list of file paths. """

    def save(file_name, content):
        """Saves file with content given in string format. Returns name of the saved file."""
        with open(Path(folder_path).joinpath(file_name), "w") as f:
            f.write(content)
        return file_name

    sif_files = [save('capacitance.sif', sif_capacitance(json_data, folder_path))]
    london_penetration_depth = json_data.get('london_penetration_depth', 0.0)
    if london_penetration_depth > 0:
        def_file = save('inductance.definitions', sif_inductance_definitions(json_data))
        sif_files.append(save('inductance.sif', sif_inductance(json_data, folder_path, def_file)))
    else:
        sif_files.append(save('capacitance0.sif', sif_capacitance(json_data, folder_path, True)))
    return sif_files


def get_cross_section_capacitance_and_inductance(json_data, folder_path):
    """Returns capacitance and inductance matrices stored in simulation output files."""
    try:
        c_matrix_file = Path(folder_path).joinpath('capacitance.dat')
        c_matrix = pd.read_csv(c_matrix_file, delim_whitespace=True, header=None).values
    except FileNotFoundError:
        return {'Cs': None, 'Ls': None}

    london_penetration_depth = json_data.get('london_penetration_depth', 0.0)
    try:
        if london_penetration_depth > 0:
            l_matrix_file = Path(folder_path).joinpath('inductance.dat')
            data = pd.read_csv(l_matrix_file, delim_whitespace=True, header=None)
            with open(f"{l_matrix_file}.names") as names:
                data.columns = [
                    line.split('res: ')[1].replace('\n', '') for line in names.readlines() if 'res:' in line
                ]
            voltage = data['v_component(1) re'] + 1.j * data['v_component(1) im']
            current = data['i_component(1) re'] + 1.j * data['i_component(1) im']
            impedance = voltage / current
            l_matrix = np.array([np.imag(impedance) / angular_frequency])
        else:
            c0_matrix_file = Path(folder_path).joinpath('capacitance0.dat')
            c0_matrix = pd.read_csv(c0_matrix_file, delim_whitespace=True, header=None).values
            l_matrix = mu_0 * epsilon_0 * np.linalg.inv(c0_matrix)
    except FileNotFoundError:
        return {'Cs': c_matrix.tolist(), 'Ls': None}

    return {'Cs': c_matrix.tolist(), 'Ls': l_matrix.tolist()}


def get_interface_quality_factors(json_data, path):
    """ Compute quality factors for interfaces with given dielectric loss tangent and energy participation"""
    interfaces = json_data['dielectric_surfaces']

    try:
        energy_data, energy_layer_data = Path(path) / 'energy.dat', Path(path) / 'energy.dat.names'
        energies = pd.read_csv(energy_data, delim_whitespace=True, header=None).values.flatten()

        with open(energy_layer_data) as fp:
            energy_layers = [
                match.group(1)
                for line in fp
                for match in re.finditer("diffusive energy: potential mask ([a-z_]+)", line)
            ]

        total_energy = energies.sum()
        energy_dict = dict(zip(energy_layers, energies))
        all_energies = {f'E_{k}': energy for k, energy in energy_dict.items()}
        # remove non-interface bodies after getting total energy
        energy_layers = frozenset(energy_layers) & frozenset(interfaces.keys())
        energy_dict = {k: energy_dict[k] for k in energy_layers}
        participations = {f'p_{k}': energy / total_energy for k, energy in energy_dict.items()}
        quality_factors = {
            f'Q_{k}': 1 / (p * interfaces[k]['tan_delta_surf'])
            for k, p in zip(energy_dict, participations.values())
        }
        quality_factors['Q_total'] = 1 / sum(1 / q for q in quality_factors.values())

        return {**all_energies, **participations, **quality_factors}

    except FileNotFoundError:
        return {'Q_total': None}
