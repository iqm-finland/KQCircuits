# This code is part of KQCircuits
# Copyright (C) 2021 IQM Finland Oy
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
from itertools import product
from pathlib import Path
from shutil import copytree

from kqcircuits.simulations.export.util import export_layers


def copy_content_into_directory(source_paths: list, path: Path, folder):
    """Create a folder and copy the contents of the source folders into it

    Arguments:
        source_paths: list of source directories from which to copy content
        path: path where the new folder will be created
        folder: name of the new folder
    """
    if path.exists() and path.is_dir():
        for source_path in source_paths:
            copytree(str(source_path), str(path.joinpath(folder)), dirs_exist_ok=True)


def get_post_process_command_lines(post_process, path, json_filenames):
    """Return post process command line calls as string. Can be used in construction of .bat or .sh script files.

    Args:
        post_process: List of PostProcess objects, a single PostProcess object, or None to be executed after simulations
        path: simulation folder path
        json_filenames: list of paths to simulation json files

    Returns:
        Command lines as string
    """
    if post_process is None:
        return ""

    commands = "echo Post-process\n"
    if isinstance(post_process, list):
        for pp in post_process:
            commands += pp.get_command_line(path, json_filenames)
    else:
        commands += post_process.get_command_line(path, json_filenames)
    return commands


def export_simulation_oas(simulations, path: Path, file_prefix="simulation"):
    """
    Write single OASIS file containing all simulations in list.
    """
    unique_layouts = {simulation.layout for simulation in simulations}
    if len(unique_layouts) != 1:
        raise ValueError("Cannot write batch OASIS file since not all simulations are on the same layout.")

    cells = [simulation.cell for simulation in simulations]
    oas_filename = str(path.joinpath(file_prefix + ".oas"))
    export_layers(oas_filename, simulations[0].layout, cells, output_format="OASIS", layers=None)
    return oas_filename


def sweep_simulation(layout, sim_class, sim_parameters, sweeps):
    """Create simulation sweep by varying one parameter at time. Return list of simulations."""
    simulations = []
    lengths = [len(l) for l in sweeps.values()]
    logging.info(f'Added simulations: {" + ".join([str(l) for l in lengths])} = {sum(lengths)}')
    for param in sweeps:
        for value in sweeps[param]:
            parameters = {
                **sim_parameters,
                param: value,
                "name": "{}_{}_{}".format(sim_parameters["name"], param, str(value)),
            }
            simulations.append(sim_class(layout, **parameters))
    return simulations


def cross_sweep_simulation(layout, sim_class, sim_parameters, sweeps):
    """Create simulation sweep by cross varying all parameters. Return list of simulations."""
    simulations = []
    keys = list(sweeps)
    sets = [list(prod) for prod in product(*sweeps.values())]
    logging.info(f'Added simulations: {" * ".join([str(len(l)) for l in sweeps.values()])} = {len(sets)}')
    for values in sets:
        parameters = {**sim_parameters}
        for i, key in enumerate(keys):
            parameters[key] = values[i]
        parameters["name"] = sim_parameters["name"] + "_" + "_".join([str(value) for value in values])
        simulations.append(sim_class(layout, **parameters))
    return simulations
