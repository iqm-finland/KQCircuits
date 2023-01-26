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
import json
import argparse

from pathlib import Path

from kqcircuits.simulations.cross_section_simulation import CrossSectionSimulation
from kqcircuits.simulations.export.elmer.elmer_export import copy_elmer_scripts_to_directory, export_elmer_script
from kqcircuits.simulations.export.util import export_layers
from kqcircuits.util.export_helper import write_commit_reference_file
from kqcircuits.util.geometry_json_encoder import GeometryJsonEncoder


def export_cross_section_elmer_json(simulation: CrossSectionSimulation, path: Path, mesh_size=None, workflow=None,
                                    dielectric_surfaces=None, linear_system_method='bicgstab', p_element_order=1,
                                    is_axisymmetric=False):
    """
    Export Elmer simulation into json and gds files.

    Args:
        simulation: The cross-section simulation to be exported.
        path: Location where to write json.
        mesh_size: Dictionary where key denotes material (string) and value (double) denotes the maximal length of mesh
            element. To refine material interface the material names by should be separated by '|' in the key. For
            example if the dictionary is {'substrate': 10, 'substrate|vacuum': 2}, the maximum mesh element length is
            10 inside the substrate and 2 on the substrate-vacuum interface.
        workflow(dict): Parameters for simulation workflow
        dielectric_surfaces: Loss tangents for dielectric interfaces, thickness and permittivity should be specified in
            the simulation. The loss tangent is post-processed to the participation to get the quality factor.
            Default is None. Input is of the form::

                'substrate': {
                    'tan_delta_surf': 5e-7
                },
                'layerMA': {  # metal–vacuum
                    'tan_delta_surf': 0.001,  # loss tangent
                },
                'layerMS': { # metal–substrate
                    'tan_delta_surf': 0.001,
                },
                'layerSA': { # substrate–vacuum
                    'tan_delta_surf': 0.001,
                }

        linear_system_method(str): Available: 'bicgstab', 'mg' (Default: bicgstab)
        p_element_order(int): polynomial order of p-elements (Default: 1)
        is_axisymmetric(bool): Simulate with Axi Symmetric coordinates along :math:`y\\Big|_{x=0}` (Default: False)

    Returns:
         Path to exported json file.
    """

    parser = argparse.ArgumentParser()

    parser.add_argument('-q', "--quiet", action='store_true')
    args, _ = parser.parse_known_args()

    workflow = {} if workflow is None else workflow

    if args.quiet:
        workflow.update(
            {
                'run_gmsh_gui': False,  # For GMSH: if true, the mesh is shown after it is done
                                       # (for large meshes this can take a long time)
                'run_paraview': False,  # this is visual view of the results
            })

    if simulation is None or not isinstance(simulation, CrossSectionSimulation):
        raise ValueError("Cannot export without simulation")

    # collect data for .json file
    layers = simulation.layer_dict
    json_data = {
        'tool': 'cross-section',
        **simulation.get_simulation_data(),
        'layers': {k: (v.layer, v.datatype) for k, v in layers.items()},
        'mesh_size': mesh_size if mesh_size is not None else dict(),
        'workflow': workflow,
        **({} if dielectric_surfaces is None else {'dielectric_surfaces': dielectric_surfaces}),
        'linear_system_method': linear_system_method,
        'p_element_order': p_element_order,
        'is_axisymmetric': is_axisymmetric,
    }

    # write .json file
    json_filename = str(path.joinpath(simulation.name + '.json'))
    with open(json_filename, 'w') as fp:
        json.dump(json_data, fp, cls=GeometryJsonEncoder, indent=4)

    # write .gds file
    gds_filename = str(path.joinpath(simulation.name + '.gds'))
    export_layers(gds_filename, simulation.layout, [simulation.cell], output_format='GDS2', layers=layers.values())

    return json_filename


def export_cross_section_elmer(simulations: [], path: Path, file_prefix='simulation', script_file='scripts/run.py',
                               mesh_size=None, workflow=None, dielectric_surfaces=None, linear_system_method='bicgstab',
                               p_element_order=1, is_axisymmetric=False, skip_errors=False):
    """
    Exports an elmer cross-section simulation model to the simulation path.

    Args:

        simulations: list of all the cross-section simulations
        path(Path): Location where to output the simulation model
        file_prefix: File prefix of the script file to be created.
        script_file: Name of the script file to run.
        mesh_size: Dictionary where key denotes material (string) and value (double) denotes the maximal length of mesh
            element. To refine material interface the material names by should be separated by '|' in the key. For
            example if the dictionary is {'substrate': 10, 'substrate|vacuum': 2}, the maximum mesh element length is
            10 inside the substrate and 2 on the substrate-vacuum interface.
        workflow(dict): Parameters for simulation workflow
        dielectric_surfaces: Loss tangents for dielectric interfaces, thickness and permittivity should be specified in
            the simulation. The loss tangent is post-processed to the participation to get the quality factor.
            Default is None. Input is of the form::

                'substrate': {
                    'tan_delta_surf': 5e-7
                },
                'layerMA': {  # metal–vacuum
                    'tan_delta_surf': 0.001,  # loss tangent
                },
                'layerMS': { # metal–substrate
                    'tan_delta_surf': 0.001,
                },
                'layerSA': { # substrate–vacuum
                    'tan_delta_surf': 0.001,
                }

        linear_system_method(str): Available: 'bicgstab', 'mg' (Default: bicgstab)
        p_element_order(int): polynomial order of p-elements (Default: 1)
        is_axisymmetric(bool): Simulate with Axi Symmetric coordinates along :math:`y\\Big|_{x=0}` (Default: False)
        skip_errors(bool): Skip simulations that cause errors. (Default: False)

            .. warning::

               **Use this carefully**, some of your simulations might not make sense physically and
               you might end up wasting time on bad simulations.

    Returns:

        Path to exported script file.
    """
    write_commit_reference_file(path)
    copy_elmer_scripts_to_directory(path)
    json_filenames = []
    for simulation in simulations:
        try:
            json_filenames.append(export_cross_section_elmer_json(simulation, path, mesh_size, workflow,
                                                                  dielectric_surfaces, linear_system_method,
                                                                  p_element_order, is_axisymmetric))
        except (IndexError, ValueError, Exception) as e:  # pylint: disable=broad-except
            if skip_errors:
                logging.warning(
                    f'Simulation {simulation.name} skipped due to {e.args}. '
                    'Some of your other simulations might not make sense geometrically. '
                    'Disable `skip_errors` to see the full traceback.'
                )
            else:
                raise UserWarning(
                    'Generating simulation failed. You can discard the errors using `skip_errors` in `export_elmer`. '
                    'Moreover, `skip_errors` enables visual inspection of failed and successful simulation '
                    'geometry files.'
                ) from e

    return export_elmer_script(json_filenames, path, workflow, file_prefix=file_prefix, script_file=script_file)
