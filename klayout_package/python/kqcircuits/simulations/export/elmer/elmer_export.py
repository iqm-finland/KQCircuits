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

from kqcircuits.simulations.export.util import export_layers
from kqcircuits.util.export_helper import write_commit_reference_file
from kqcircuits.defaults import ELMER_SCRIPT_PATHS
from kqcircuits.simulations.simulation import Simulation
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


def export_elmer_json(simulation: Simulation,
                      path: Path,
                      tool='capacitance',
                      linear_system_method='bicgstab',
                      p_element_order=1,
                      frequency=5,
                      mesh_size=None,
                      workflow=None):
    """
    Export Elmer simulation into json and gds files.

    Args:
        simulation: The simulation to be exported.
        path: Location where to write json.
        tool(str): Available: "capacitance" and "wave_equation" (Default: capacitance)
        linear_system_method(str): Available: 'bicgstab', 'mg' (Default: bicgstab)
        p_element_order(int): polynomial order of p-elements (Default: 1)
        frequency: Units are in GHz. To set up multifrequency analysis, use list of numbers.
        mesh_size(dict): Parameters to determine mesh element sizes
        workflow(dict): Parameters for simulation workflow

    Returns:
         Path to exported json file.
    """
    if simulation is None or not isinstance(simulation, Simulation):
        raise ValueError("Cannot export without simulation")

    # collect data for .json file
    json_data = {
        'tool': tool,
        'linear_system_method': linear_system_method,
        'p_element_order': p_element_order,
        **simulation.get_simulation_data(),
        'mesh_size': {} if mesh_size is None else mesh_size,
        'workflow': {} if workflow is None else workflow,
        'frequency': frequency,
    }

    # write .json file
    json_filename = str(path.joinpath(simulation.name + '.json'))
    with open(json_filename, 'w') as fp:
        json.dump(json_data, fp, cls=GeometryJsonEncoder, indent=4)

    # write .gds file
    gds_filename = str(path.joinpath(simulation.name + '.gds'))
    export_layers(gds_filename, simulation.layout, [simulation.cell], output_format='GDS2',
                  layers=simulation.get_layers())

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
    if sbatch:
        sbatch_parameters = workflow['sbatch_parameters']
        elmer_n_processes = sbatch_parameters['--ntasks']
    python_executable = workflow.get('python_executable', 'python')
    parallelize_workload = 'n_workers' in workflow


    main_script_filename = str(path.joinpath(file_prefix + '.sh'))
    with open(main_script_filename, 'w') as main_file:

        if parallelize_workload and not sbatch:
            main_file.write('{} scripts/simple_workload_manager.py {}'.format(python_executable, workflow['n_workers']))

        script_filenames = []
        for i, json_filename in enumerate(json_filenames):
            with open(json_filename) as f:
                json_data = json.load(f)
                simulation_name = json_data['parameters']['name']
            script_filename = str(path.joinpath(simulation_name + '.sh'))
            script_filenames.append(script_filename)
            with open(script_filename, 'w') as file:
                if sbatch:
                    file.write('#!/bin/bash\n')
                    file.write('#SBATCH --job-name={}_{}\n'.format(sbatch_parameters['--job-name'], str(i)))
                    file.write('#SBATCH --account={}\n'.format(sbatch_parameters['--account']))
                    file.write('#SBATCH --partition={}\n'.format(sbatch_parameters['--partition']))
                    file.write('#SBATCH --time={}\n'.format(sbatch_parameters['--time']))
                    file.write('#SBATCH --ntasks={}\n'.format(elmer_n_processes))
                    file.write('#SBATCH --cpus-per-task={}\n'.format(sbatch_parameters['--cpus-per-task']))
                    file.write('#SBATCH --mem-per-cpu={}\n'.format(sbatch_parameters['--mem-per-cpu']))
                    file.write('\n')
                    file.write('# set the number of threads based on --cpus-per-task\n')
                    file.write('export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK\n')
                    file.write('\n')
                    file.write('echo "Simulation {}/{} Gmsh"\n'.format(i + 1, len(json_filenames)))
                    file.write('srun -n 1 {2} "{0}" "{1}" --only-gmsh -q 2>&1 >> "{1}_Gmsh.log"\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                        )
                    file.write('echo "Simulation {}/{} ElmerGrid"\n'.format(i + 1, len(json_filenames)))
                    file.write('ElmerGrid 14 2 "{0}" 2>&1 >> "{1}_ElmerGrid.log"\n'.format(
                        simulation_name + ".msh",
                        Path(json_filename).relative_to(path))
                    )
                    file.write('ElmerGrid 2 2 "{0}" 2>&1 -metis {1} 4 --partdual --removeunused >> '\
                            '"{2}_ElmerGrid_part.log"\n'.format(
                        simulation_name,
                        str(elmer_n_processes),
                        Path(json_filename).relative_to(path))
                    )

                    file.write('echo "Simulation {}/{} Elmer"\n'.format(i + 1, len(json_filenames)))
                    file.write('srun --cpu-bind none -n {} ElmerSolver_mpi "sif/{}.sif" 2>&1 >> '\
                            '"{}_Elmer.log"\n'.format(
                                elmer_n_processes,
                                simulation_name,
                                Path(json_filename).relative_to(path)
                                ))
                    file.write('echo "Simulation {}/{} write results json"\n'.format(i + 1, len(json_filenames)))
                    file.write('srun -n 1 {2} "{0}" "{1}" --write-project-results 2>&1 >> '\
                            '{1}_write_project_results.log\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                    )

                    file.write('echo "Simulation {}/{} write versions json"\n'.format(i + 1, len(json_filenames)))
                    file.write('srun -n 1 {2} "{0}" "{1}" --write-versions-file 2>&1 >> '\
                            '{1}_write_versions_file.log\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                    )
                else:
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

            if sbatch:
                main_file.write('echo "Submitting the main script of simulation {}/{}"\n'
                        .format(i + 1, len(json_filenames)))
                main_file.write('echo "--------------------------------------------"\n')
                main_file.write('sbatch "{}"\n'.format(Path(script_filename).relative_to(path)))
            elif parallelize_workload:
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


def export_elmer(simulations: [],
                 path: Path,
                 tool='capacitance',
                 linear_system_method='bicgstab',
                 p_element_order=1,
                 frequency=5,
                 file_prefix='simulation',
                 script_file='scripts/run.py',
                 mesh_size=None,
                 workflow=None,
                 skip_errors=False):
    """
    Exports an elmer simulation model to the simulation path.

    Args:

        simulations(list(Simulation)): list of all the simulations
        path(Path): Location where to output the simulation model
        tool(str): Available: "capacitance" and "wave_equation" (Default: capacitance)
        linear_system_method(str): Available: 'bicgstab', 'mg' (Default: bicgstab)
        p_element_order(int): polynomial order of p-elements (Default: 1)
        frequency: Units are in GHz. To set up multifrequency analysis, use list of numbers.
        file_prefix: File prefix of the script file to be created.
        script_file: Name of the script file to run.
        mesh_size(dict): Parameters to determine mesh element sizes
        workflow(dict): Parameters for simulation workflow
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
            json_filenames.append(export_elmer_json(simulation, path, tool, linear_system_method,
                                                    p_element_order, frequency, mesh_size, workflow))
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
