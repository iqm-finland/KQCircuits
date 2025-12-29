# This code is part of KQCircuits
# Copyright (C) 2025 IQM Finland Oy
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
Reruns all simulations in the `input_file` main script which do not have a project_results.json file.
If no `-o outfile` argument is written, writes the new script as `input_file` with added `_rerun` suffix.

Supports both Ansys and Elmer simulations, but post processing scripts need to be run manually afterwards

Elmer simulations exported using `n_workers > 1` are run serially, but with multiple multiple MPI processes
unless an argument ``-n 1`` is provided to this script.
"""

import subprocess
from pathlib import Path
import json
import platform
import argparse
import re


def _run_cmd(cmd, error_str=""):
    try:
        if platform.system() == "Windows":  # Windows
            subprocess.check_call(cmd, shell=True)
        else:
            subprocess.check_call(["bash", cmd])
    except subprocess.CalledProcessError:
        print(error_str)


def _force_serial_workflow(filename):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["workflow"]["n_workers"] = 1
    cpu_count = args.n_processes or data["workflow"]["local_machine_cpu_count"]
    data["workflow"]["elmer_n_processes"] = cpu_count
    data["workflow"]["gmsh_n_threads"] = cpu_count
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


parser = argparse.ArgumentParser()

parser.add_argument("input_file", type=str, help="Main sh or bat file used to run the simulations")
parser.add_argument(
    "-o", "--output-file", help="Name of the output file. Defaults to adding the suffix `_rerun` to `args.input_file`"
)
parser.add_argument("-n", "--n-processes", type=int, help="Number of MPI processes in Elmer and threads in Gmsh")
args, unknown = parser.parse_known_args()

input_file = args.input_file
script_name, _, extension = input_file.rpartition(".")
output_file = args.output_file or f"{script_name}_rerun.{extension}"

completed_simulations = [str(s).removesuffix("_project_results.json") for s in Path(".").glob("*project_results.json")]
missing = set()

with open(input_file, "r", encoding="utf-8") as f:
    script_contents = f.readlines()

if extension == "sh":
    rerun_script = script_contents[:1]
    for line in script_contents[1:]:
        matches = re.findall(r'"\./(.*?)\.sh"', line)
        for sim_name in matches:
            json_name = f"{sim_name}.json"
            if sim_name not in completed_simulations and Path(json_name).exists():
                _force_serial_workflow(json_name)
                rerun_script.append(f"./{sim_name}.sh\n")
                missing.add(sim_name)

elif extension == "bat":
    # Consider Ansys simulations with .sNp files as completed
    snp_pattern = re.compile(r"^(.*)_project_SMatrix\.s\d+p$")
    for p in Path(".").glob("*_project_SMatrix.s*p"):
        snp_m = snp_pattern.search(p.name)
        if snp_m:
            completed_simulations.add(snp_m.group(1))

    rerun_script = script_contents[:4]
    for line in script_contents[4:]:
        matches = re.findall(r'-scriptargs\s+"(.*?)\.json"', line)
        if matches:
            if matches[0] not in completed_simulations and Path(f"{matches[0]}.json").exists():
                rerun_script.append(line)
                missing.add(matches[0])
else:
    raise ValueError(f'Unknown main script extension: "{extension}" ')


if missing:
    sim_tool = "Elmer" if extension == "sh" else "Ansys"
    print(f"Missing {len(missing)} {sim_tool} simulations:")
    print(missing)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("".join(rerun_script))

    print("Do you want to run the simulations now? (y to continue):")
    if input().lower().startswith("y"):
        _run_cmd(output_file, error_str=f"Error in rerunning {sim_tool} simulations")
    else:
        print(f"Simulations can be launched manually by running `{output_file}`")
else:
    print("No missing results found")
