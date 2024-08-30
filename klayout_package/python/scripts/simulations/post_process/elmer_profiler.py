# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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


"""
Produces table of runtimes for gmsh and Elmer and the number of mesh tetrahedron from Elmer results
"""

import re
import os
import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "util"))
from post_process_helpers import (  # pylint: disable=wrong-import-position, no-name-in-module
    find_varied_parameters,
    tabulate_into_csv,
)


def _load_elmer_runtimes(path: Path, name: str, elmer_n_processes: int) -> dict:
    """Parse Elmer log files in path/log_files for the runtimes and sum the results if multiple files
    are found with endings "", "_C", "_L", "_C0".

    Multiplies the CPU time reported by elmer by elmer_n_processes to get realistic CPU runtime
    """
    logs_folder = Path(path).joinpath("log_files")

    times = {}

    endings = ["", "_C", "_L", "_C0"]
    for end in endings:
        log_file = logs_folder.joinpath(name + end + ".Elmer.log")
        if log_file.is_file():
            with open(log_file, "r", encoding="utf-8") as f:
                for line in reversed(f.readlines()):
                    if "SOLVER TOTAL TIME(CPU,REAL):" in line:
                        sp_line = line.rstrip().split()
                        times["elmer_time_cpu"] = times.get("elmer_time_cpu", 0) + float(sp_line[-2])
                        times["elmer_time_real"] = times.get("elmer_time_real", 0) + float(sp_line[-1])
                        break

    if not times:
        logging.warning(f"No log file found for {name}")

    times["elmer_time_cpu"] = elmer_n_processes * times["elmer_time_cpu"]
    return times


def _load_elmer_elements(path: Path, name: str) -> dict:
    """Parse path/mesh.header for the number of mesh elements used in Elmer"""
    log_file = Path(path).joinpath(name).joinpath("mesh.header")
    if log_file.is_file():
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                return {"elmer_elements": line.rstrip().split()[1]}
    else:
        logging.warning(f"No file found at {log_file}")
        return {}


def _load_gmsh_data(path: Path, name: str) -> dict:
    """Parse Gmsh log file found in path/log_files for the CPU and real runtimes"""
    log_file = Path(path).joinpath("log_files").joinpath(name + ".Gmsh.log")

    if log_file.is_file():
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Sum times used for meshing lines (1D), surfaces (2D) and volumes (3D) which
        # are reported separately by Gmsh
        search_str = r"\s+(\d+\.\d+)"
        times = [[0], [0]]
        for line in lines:
            if "Info    : Done meshing " in line:
                for i, s in enumerate(("Wall", "CPU")):
                    match = re.search(s + search_str, line)
                    if match:
                        times[i].append(float(match.group(1)))
        return {"gmsh_time_real": sum(times[0]), "gmsh_time_cpu": sum(times[1])}
    else:
        logging.warning(f"No log file found at {log_file}")
        return {}


def _load_workflow_data(definition_file: Path) -> dict:
    """Load relevant parts of workflow dict"""
    with open(definition_file, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    return {key: json_data["workflow"][key] for key in ("elmer_n_processes", "elmer_n_threads", "gmsh_n_threads")}


# Find data files
path = os.path.curdir
names = [f.removesuffix("_project_results.json") for f in os.listdir(path) if f.endswith("_project_results.json")]
if names:
    # Find parameters that are swept
    definition_files = [f + ".json" for f in names]
    parameters, parameter_values = find_varied_parameters(definition_files)

    # Load result data
    res = {}
    for key, name, definition_file in zip(parameter_values.keys(), names, definition_files):
        workflow_data = _load_workflow_data(definition_file)
        res[key] = {
            **workflow_data,
            **_load_gmsh_data(path, name),
            **_load_elmer_runtimes(path, name, workflow_data["elmer_n_processes"]),
            **_load_elmer_elements(path, name),
        }

    tabulate_into_csv(f"{os.path.basename(os.path.abspath(path))}_profile.csv", res, parameters, parameter_values)
