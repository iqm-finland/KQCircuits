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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).

import logging
import json
from itertools import product
from pathlib import Path
from shutil import copytree
from typing import Sequence

from kqcircuits.simulations.export.util import export_layers
from kqcircuits.util.geometry_json_encoder import GeometryJsonEncoder


def get_combined_parameters(simulation, solution):
    """Return parameters of Simulation and Solution in a combined dictionary.
    In case of common keys, 'solution.' prefix is added to Solution parameter key.
    """
    sim_dict = simulation.get_parameters()
    sol_dict = solution.get_parameters()
    return {
        **{k: v for k, v in sim_dict.items() if k != "name"},
        **{f"solution.{k}" if k in sim_dict else k: v for k, v in sol_dict.items() if k != "name"},
    }


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


def export_simulation_json(json_data, json_file_path):
    """Export simulation definitions json. Raise an error if file exists"""
    if not Path(json_file_path).exists():
        with open(json_file_path, "w", encoding="utf-8") as fp:
            json.dump(json_data, fp, cls=GeometryJsonEncoder, indent=4)
    else:
        raise ValueError(
            f"Json file '{json_file_path}' already exists. Make sure that simulations and solutions have unique names."
        )


def export_simulation_oas(simulations, path: Path, file_prefix="simulation"):
    """
    Write single OASIS file containing all simulations in list.
    """
    simulations = [simulation[0] if isinstance(simulation, Sequence) else simulation for simulation in simulations]
    unique_layouts = {simulation.layout for simulation in simulations}
    if len(unique_layouts) != 1:
        raise ValueError("Cannot write batch OASIS file since not all simulations are on the same layout.")

    cells = [simulation.cell for simulation in simulations]
    oas_filename = str(path.joinpath(file_prefix + ".oas"))
    export_layers(oas_filename, simulations[0].layout, cells, output_format="OASIS", layers=None)
    return oas_filename


def _join_flat_str(value):
    """Returns string in which value is flattened and joined using underscore separator."""
    if isinstance(value, str):
        return value  # return string as it is
    if isinstance(value, dict):
        return _join_flat_str(value.items())  # join keys and values of dictionary
    try:
        return "_".join([_join_flat_str(v) for v in value])  # join terms of any iterable
    except TypeError:
        return str(value)  # convert any non-iterable to string


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
                "name": _join_flat_str((sim_parameters.get("name", ""), param, value)),
            }
            simulations.append(sim_class(**parameters) if layout is None else sim_class(layout, **parameters))
    return simulations


def cross_sweep_simulation(layout, sim_class, sim_parameters, sweeps):
    """Create simulation sweep by cross-varying all parameters. Return list of simulations."""
    simulations = []
    keys = list(sweeps)
    sets = [list(prod) for prod in product(*sweeps.values())]
    logging.info(f'Added simulations: {" * ".join([str(len(l)) for l in sweeps.values()])} = {len(sets)}')
    for values in sets:
        parameters = {**sim_parameters}
        for i, key in enumerate(keys):
            parameters[key] = values[i]
        parameters["name"] = _join_flat_str((sim_parameters.get("name", ""), values))
        simulations.append(sim_class(**parameters) if layout is None else sim_class(layout, **parameters))
    return simulations


def sweep_solution(sol_class, sol_parameters, sweeps):
    """Create solution sweep by varying one parameter at time. Return list of solutions."""
    return sweep_simulation(None, sol_class, sol_parameters, sweeps)


def cross_sweep_solution(sol_class, sol_parameters, sweeps):
    """Create solution sweep by cross-varying all parameters. Return list of solutions."""
    return cross_sweep_simulation(None, sol_class, sol_parameters, sweeps)


def cross_combine(simulations, solutions):
    """Combines simulations and solutions into list of tuples.

    Args:
        simulations: A Simulation object or a list of Simulation objects.
        solutions: A Solution object or a list of Solution objects.
    Returns:
        A list of tuples containing all combinations of simulations and solutions.

    """
    return list(
        product(
            simulations if isinstance(simulations, Sequence) else [simulations],
            solutions if isinstance(solutions, Sequence) else [solutions],
        )
    )
