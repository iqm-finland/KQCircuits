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
import stat
import logging
import json
import argparse

from pathlib import Path
from distutils.dir_util import copy_tree
from typing import Sequence

from kqcircuits.simulations.export.util import export_layers
from kqcircuits.util.export_helper import write_commit_reference_file
from kqcircuits.defaults import ELMER_SCRIPT_PATHS
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.simulations.cross_section_simulation import CrossSectionSimulation
from kqcircuits.util.geometry_json_encoder import GeometryJsonEncoder


def copy_elmer_scripts_to_directory(path: Path):
    """
    Copies Elmer scripts into directory path.

    Args:
        path: Location where to copy scripts folder.
    """
    if path.exists() and path.is_dir():
        for script_path in ELMER_SCRIPT_PATHS:
            copy_tree(str(script_path), str(path), update=1)


def export_elmer_json(simulation,
                      path: Path,
                      tool='capacitance',
                      linear_system_method='bicgstab',
                      p_element_order=1,
                      frequency=5,
                      mesh_size=None,
                      boundary_conditions=None,
                      workflow=None,
                      percent_error=0.005,
                      max_error_scale=2,
                      max_outlier_fraction=1e-3,
                      maximum_passes=1,
                      minimum_passes=1,
                      dielectric_surfaces=None,
                      is_axisymmetric=False):
    """
    Export Elmer simulation into json and gds files.

    Args:
        simulation: The simulation to be exported.
        path: Location where to write json.
        tool(str): Available: "capacitance", "wave_equation" and "cross-section" (Default: capacitance)
        linear_system_method(str): Available: 'bicgstab', 'mg' (Default: bicgstab)
        p_element_order(int): polynomial order of p-elements (Default: 1)
        frequency: Units are in GHz. To set up multifrequency analysis, use list of numbers.
        mesh_size(dict): Parameters to determine mesh element sizes
        boundary_conditions(dict): Parameters to determine boundary conditions
        workflow(dict): Parameters for simulation workflow
        percent_error(float): Stopping criterion in adaptive meshing.
        max_error_scale(float): Maximum element error, relative to percent_error, allowed in individual elements.
        max_outlier_fraction(float): Maximum fraction of outliers from the total number of elements
        maximum_passes(int): Maximum number of adaptive meshing iterations.
        minimum_passes(int): Minimum number of adaptive meshing iterations.
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
        is_axisymmetric(bool): Simulate with Axi Symmetric coordinates along :math:`y\\Big|_{x=0}` (Default: False)

    Returns:
         Path to exported json file.
    """
    is_cross_section = isinstance(simulation, CrossSectionSimulation)

    if simulation is None or not isinstance(simulation, (Simulation, CrossSectionSimulation)):
        raise ValueError("Cannot export without simulation")

    # collect data for .json file
    if is_cross_section:
        layers = simulation.layer_dict

    json_data = {
        'tool': tool,
        **simulation.get_simulation_data(),
        **({'layers': {k: (v.layer, v.datatype) for k, v in layers.items()}} if is_cross_section else {}),
        'mesh_size': {} if mesh_size is None else mesh_size,
        'boundary conditions': boundary_conditions,
        'workflow': {} if workflow is None else workflow,
        'percent_error': percent_error,
        'max_error_scale': max_error_scale,
        'max_outlier_fraction': max_outlier_fraction,
        'maximum_passes': maximum_passes,
        'minimum_passes': minimum_passes,
        'frequency': frequency,
        **({} if dielectric_surfaces is None else {'dielectric_surfaces': dielectric_surfaces}),
        'linear_system_method': linear_system_method,
        'p_element_order': p_element_order,
        'is_axisymmetric': is_axisymmetric,
    }

    if is_cross_section:
        if json_data.get('london_penetration_depth', 0.0) > 0:
            sif_names = ['capacitance', 'inductance']
        else:
            sif_names = ['capacitance', 'capacitance0']
    else:
        sif_names = [json_data['parameters']['name']]

    json_data['sif_names'] = sif_names

    # write .json file
    json_filename = str(path.joinpath(simulation.name + '.json'))
    with open(json_filename, 'w') as fp:
        json.dump(json_data, fp, cls=GeometryJsonEncoder, indent=4)

    # write .gds file
    gds_filename = str(path.joinpath(simulation.name + '.gds'))
    export_layers(
        gds_filename,
        simulation.layout,
        [simulation.cell],
        output_format='GDS2',
        layers=layers.values() if is_cross_section else simulation.get_layers()
    )

    return json_filename


def export_elmer_script(json_filenames, path: Path, workflow=None, file_prefix='simulation',
        script_file='scripts/run.py'):
    """
    Create script files for running one or more simulations.
    Create also a main script to launch all the simulations at once.

    Args:
        json_filenames: List of paths to json files to be included into the script.
        path: Location where to write the script file.
        workflow(dict): Parameters for simulation workflow
        file_prefix: Name of the script file to be created.
        script_file: Name of the script file to run.

    Returns:

        Path of exported main script file
    """
    if workflow is None:
        workflow = dict()
    sbatch = 'sbatch_parameters' in workflow
    python_executable = workflow.get('python_executable', 'python')
    parallelize_workload = 'n_workers' in workflow

    main_script_filename = str(path.joinpath(file_prefix + '.sh'))

    if sbatch:
        sbatch_parameters = workflow['sbatch_parameters']

        if sbatch_parameters.get('--account', 'project_0') == 'project_0':
            logging.warning('Remote account not set or "project_0"!')

        common_keys = [k for k in sbatch_parameters.keys() if k.startswith('--')]
        sbatch_settings_elmer = {k: sbatch_parameters.pop(k) for k in common_keys}

        sbatch_settings_meshes = sbatch_settings_elmer.copy()

        sbatch_settings_elmer['--time'] = sbatch_parameters.pop('elmer_time', '00:10:00')
        sbatch_settings_elmer['--nodes'] = sbatch_parameters.pop('elmer_n_nodes', 1)
        sbatch_settings_elmer['--ntasks'] = sbatch_parameters.pop('elmer_n_processes', 10)
        sbatch_settings_elmer['--cpus-per-task'] = sbatch_parameters.pop('elmer_n_threads', 1)
        sbatch_settings_elmer['--mem'] = sbatch_parameters.pop('elmer_mem', '64G')

        sbatch_settings_meshes['--time'] = sbatch_parameters.pop('gmsh_time', '00:10:00')
        sbatch_settings_meshes['--nodes'] = 1
        sbatch_settings_meshes['--ntasks'] = 1
        sbatch_settings_meshes['--cpus-per-task'] = sbatch_parameters.pop('gmsh_n_threads', 10)
        sbatch_settings_meshes['--mem'] = sbatch_parameters.pop('gmsh_mem', '64G')

        if len(sbatch_parameters) > 0:
            logging.warning("Unused sbatch parameters: ")
            for k, v in sbatch_parameters.items():
                logging.warning(f"{k} : {v}")

        gmsh_n_threads = sbatch_settings_meshes['--cpus-per-task']
        elmer_n_processes = sbatch_settings_elmer['--ntasks']
        elmer_n_threads = sbatch_settings_elmer['--cpus-per-task']

        main_script_filename_meshes = str(path.joinpath(file_prefix + '_meshes.sh'))
        with open(main_script_filename_meshes, 'w') as main_file:
            main_file.write('#!/bin/bash\n')

            for s_key, s_value in sbatch_settings_meshes.items():
                main_file.write(f'#SBATCH {s_key}={s_value}\n')

            main_file.write('\n')
            main_file.write('# set the number of threads based on --cpus-per-task\n')
            main_file.write('export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK\n')
            main_file.write('\n')

            for i, json_filename in enumerate(json_filenames):
                with open(json_filename) as f:
                    json_data = json.load(f)
                    simulation_name = json_data['parameters']['name']

                sif_names = json_data['sif_names']

                script_filename_meshes = str(path.joinpath(simulation_name + '_meshes.sh'))
                with open(script_filename_meshes, 'w') as file:
                    file.write('echo "Simulation {}/{} Gmsh"\n'.format(i + 1, len(json_filenames)))
                    file.write('srun -c {3} {2} "{0}" "{1}" --only-gmsh -q 2>&1 >> '\
                            '"{1}_Gmsh.log"\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable,
                        str(gmsh_n_threads)
                        ))
                    file.write('echo "Simulation {}/{} ElmerGrid"\n'.format(i + 1, len(json_filenames)))
                    file.write('srun -c {2} ElmerGrid 14 2 "{0}" 2>&1 >> "{1}_ElmerGrid.log"\n'.format(
                        simulation_name + ".msh",
                        Path(json_filename).relative_to(path),
                        str(gmsh_n_threads)
                    ))
                    if int(elmer_n_processes) > 1:
                        file.write('srun -c {3} ElmerGrid 2 2 "{0}" 2>&1 -metis {1} 4 --partdual --removeunused >> '\
                                '"{2}_ElmerGrid_part.log"\n'.format(
                            simulation_name,
                            str(elmer_n_processes),
                            Path(json_filename).relative_to(path),
                            str(gmsh_n_threads)
                        ))
                    file.write('echo "Simulation {}/{} Write Elmer sif files"\n'.format(i + 1, len(json_filenames)))
                    file.write('srun -c {3} {2} "{0}" "{1}" --only-elmer-sifs -q 2>&1 >> "{1}_Elmer.log"\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable,
                        str(gmsh_n_threads)
                    ))
                os.chmod(script_filename_meshes, os.stat(script_filename_meshes).st_mode | stat.S_IEXEC)

                main_file.write('echo "Submitting gmsh and ElmerGrid part {}/{}"\n'
                            .format(i + 1, len(json_filenames)))
                main_file.write('echo "--------------------------------------------"\n')
                main_file.write('source "{}"\n'.format(Path(script_filename_meshes).relative_to(path)))

        # change permission
        os.chmod(main_script_filename_meshes, os.stat(main_script_filename_meshes).st_mode | stat.S_IEXEC)

        with open(main_script_filename, 'w') as main_file:
            main_file.write('#!/bin/bash\n')

            for s_key, s_value in sbatch_settings_elmer.items():
                main_file.write(f'#SBATCH {s_key}={s_value}\n')

            main_file.write('\n')
            main_file.write('# set the number of threads based on --cpus-per-task\n')
            main_file.write('export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK\n')
            main_file.write('\n')
            for i, json_filename in enumerate(json_filenames):
                with open(json_filename) as f:
                    json_data = json.load(f)
                    simulation_name = json_data['parameters']['name']

                sif_names = json_data['sif_names']
                script_filename = str(path.joinpath(simulation_name + '.sh'))
                with open(script_filename, 'w') as file:

                    file.write('echo "Simulation {}/{} Elmer"\n'.format(i + 1, len(json_filenames)))
                    for sif in sif_names:
                        file.write('srun --cpu-bind none -n {0} -c {4} ElmerSolver_mpi '\
                                '"{1}/{2}.sif" 2>&1 >> "{3}_Elmer.log"\n'.format(
                                    elmer_n_processes,
                                    simulation_name,
                                    sif,
                                    Path(json_filename).relative_to(path),
                                    elmer_n_threads
                                    ))
                    file.write('echo "Simulation {}/{} write results json"\n'.format(i + 1, len(json_filenames)))
                    file.write('srun -n 1 -c {3} {2} "{0}" "{1}" --write-project-results 2>&1 >> '\
                            '{1}_write_project_results.log\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable,
                        elmer_n_threads
                    ))

                    file.write('echo "Simulation {}/{} write versions json"\n'.format(i + 1, len(json_filenames)))
                    file.write('srun -n 1 -c {3} {2} "{0}" "{1}" --write-versions-file 2>&1 >> '\
                            '{1}_write_versions_file.log\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable,
                        elmer_n_threads
                    ))
                os.chmod(script_filename, os.stat(script_filename).st_mode | stat.S_IEXEC)

            main_file.write('echo "Submitting ElmerSolver part{}/{}"\n'
                        .format(i + 1, len(json_filenames)))
            main_file.write('echo "--------------------------------------------"\n')
            main_file.write('source "{}"\n'.format(Path(script_filename).relative_to(path)))


    else:

        with open(main_script_filename, 'w') as main_file:

            if parallelize_workload and not sbatch:
                main_file.write('{} scripts/simple_workload_manager.py {}'.format(
                    python_executable,
                    workflow['n_workers']
                ))

            for i, json_filename in enumerate(json_filenames):
                with open(json_filename) as f:
                    json_data = json.load(f)
                    simulation_name = json_data['parameters']['name']

                sif_names = json_data['sif_names']

                script_filename = str(path.joinpath(simulation_name + '.sh'))
                with open(script_filename, 'w') as file:
                    file.write('echo "Simulation {}/{} Gmsh"\n'.format(i + 1, len(json_filenames)))
                    file.write('{2} "{0}" "{1}" --only-gmsh 2>&1 >> "{1}_Gmsh.log"\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                    )
                    file.write('echo "Simulation {}/{} ElmerGrid"\n'.format(i + 1, len(json_filenames)))
                    file.write('{2} "{0}" "{1}" --only-elmergrid 2>&1 >> "{1}_ElmerGrid.log"\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                    )
                    file.write('echo "Simulation {}/{} Write Elmer sif files"\n'.format(i + 1, len(json_filenames)))
                    file.write('{2} "{0}" "{1}" --only-elmer-sifs 2>&1 >> "{1}_Elmer.log"\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                        )
                    file.write('echo "Simulation {}/{} Elmer"\n'.format(i + 1, len(json_filenames)))
                    file.write('{2} "{0}" "{1}" --only-elmer 2>&1 >> "{1}_Elmer.log"\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                    )
                    file.write('echo "Simulation {}/{} Paraview"\n'.format(i + 1, len(json_filenames)))
                    file.write('{2} "{0}" "{1}" --only-paraview\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                    )

                    file.write('echo "Simulation {}/{} write results json"\n'.format(i + 1, len(json_filenames)))
                    file.write('{2} "{0}" "{1}" --write-project-results 2>&1 >> '\
                            '"{1}_write_project_results.log"\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                    )

                    file.write('echo "Simulation {}/{} write versions file"\n'.format(i + 1, len(json_filenames)))
                    file.write('{2} "{0}" "{1}" --write-versions-file\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                    )
                # change permission
                os.chmod(script_filename, os.stat(script_filename).st_mode | stat.S_IEXEC)
                if parallelize_workload:
                    main_file.write(' "./{}"'.format(
                        Path(script_filename).relative_to(path))
                    )
                else:
                    main_file.write('echo "Submitting the main script of simulation {}/{}"\n'
                            .format(i + 1, len(json_filenames)))
                    main_file.write('echo "--------------------------------------------"\n')
                    main_file.write('"./{}"\n'.format(Path(script_filename).relative_to(path)))

    # change permission
    os.chmod(main_script_filename, os.stat(main_script_filename).st_mode | stat.S_IEXEC)

    return main_script_filename


def export_elmer(simulations: Sequence[Simulation],
                 path: Path,
                 tool='capacitance',
                 linear_system_method='bicgstab',
                 p_element_order=3,
                 frequency=5,
                 file_prefix='simulation',
                 script_file='scripts/run.py',
                 mesh_size=None,
                 boundary_conditions=None,
                 workflow=None,
                 percent_error=0.005,
                 max_error_scale=2,
                 max_outlier_fraction=1e-3,
                 maximum_passes=1,
                 minimum_passes=1,
                 dielectric_surfaces=None,
                 is_axisymmetric=False,
                 skip_errors=False):
    """
    Exports an elmer simulation model to the simulation path.

    Args:

        simulations(list(Simulation)): list of all the simulations
        path(Path): Location where to output the simulation model
        tool(str): Available: "capacitance", "wave_equation" and "cross-section" (Default: capacitance)
        linear_system_method(str): Available: 'bicgstab', 'mg' (Default: bicgstab)
        p_element_order(int): polynomial order of p-elements (Default: 1)
        frequency: Units are in GHz. To set up multifrequency analysis, use list of numbers.
        file_prefix: File prefix of the script file to be created.
        script_file: Name of the script file to run.
        mesh_size(dict): Parameters to determine mesh element sizes
        boundary_conditions(dict): Parameters to determine boundary conditions
        workflow(dict): Parameters for simulation workflow
        percent_error(float): Stopping criterion in adaptive meshing.
        max_error_scale(float): Maximum element error, relative to percent_error, allowed in individual elements.
        max_outlier_fraction(float): Maximum fraction of outliers from the total number of elements
        maximum_passes(int): Maximum number of adaptive meshing iterations.
        minimum_passes(int): Minimum number of adaptive meshing iterations.
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
        is_axisymmetric(bool): Simulate with Axi Symmetric coordinates along :math:`y\\Big|_{x=0}` (Default: False)
        skip_errors(bool): Skip simulations that cause errors. (Default: False)

            .. warning::

               **Use this carefully**, some of your simulations might not make sense physically and
               you might end up wasting time on bad simulations.

    Returns:

        Path to exported script file.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('-q', "--quiet", action='store_true')
    args, _ = parser.parse_known_args()

    if args.quiet:
        workflow.update(
            {
                'run_gmsh_gui': False,  # For GMSH: if true, the mesh is shown after it is done
                                       # (for large meshes this can take a long time)
                'run_paraview': False,  # this is visual view of the results
            })

    write_commit_reference_file(path)
    copy_elmer_scripts_to_directory(path)
    json_filenames = []
    for simulation in simulations:
        try:
            json_filenames.append(
                export_elmer_json(
                    simulation=simulation,
                    path=path,
                    tool=tool,
                    linear_system_method=linear_system_method,
                    p_element_order=p_element_order,
                    frequency=frequency,
                    mesh_size=mesh_size,
                    boundary_conditions=boundary_conditions,
                    workflow=workflow,
                    percent_error=percent_error,
                    max_error_scale=max_error_scale,
                    max_outlier_fraction=max_outlier_fraction,
                    maximum_passes=maximum_passes,
                    minimum_passes=minimum_passes,
                    dielectric_surfaces=dielectric_surfaces,
                    is_axisymmetric=is_axisymmetric
                )
            )
        except (IndexError, ValueError, Exception) as e:  # pylint: disable=broad-except
            if skip_errors:
                logging.warning(
                    f'Simulation {simulation.name} skipped due to {e.args}. '\
                    'Some of your other simulations might not make sense geometrically. '\
                    'Disable `skip_errors` to see the full traceback.'
                )
            else:
                raise UserWarning(
                    'Generating simulation failed. You can discard the errors using `skip_errors` in `export_elmer`. '\
                    'Moreover, `skip_errors` enables visual inspection of failed and successful simulation '\
                    'geometry files.'
                ) from e

    return export_elmer_script(json_filenames, path, workflow, file_prefix=file_prefix, script_file=script_file)
