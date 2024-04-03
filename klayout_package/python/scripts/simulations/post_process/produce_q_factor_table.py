# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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
"""
Produces quality factor table from Ansys or Elmer results

Args:
    sys.argv[1]: parameter file name, where the file includes loss tangents for different layers

"""
import json
import os
import sys
import csv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "util"))
from post_process_helpers import (  # pylint: disable=wrong-import-position, no-name-in-module
    find_varied_parameters,
    tabulate_into_csv,
)

with open(sys.argv[1], "r") as fp:
    loss_tangents = json.load(fp)

# Find data files
path = os.path.curdir
result_files = [f for f in os.listdir(path) if f.endswith("_project_energy.csv") or f.endswith("_project_results.json")]
if result_files:
    # Find parameters that are swept
    definition_files = [
        (
            f.replace("_project_results.json", ".json")
            if f.endswith("_project_results.json")
            else f.replace("_project_energy.csv", ".json")
        )
        for f in result_files
    ]
    parameters, parameter_values = find_varied_parameters(definition_files)

    # Load result data
    q = {}
    for key, result_file in zip(parameter_values.keys(), result_files):
        if result_file.endswith("_project_results.json"):
            # read results from Elmer output
            with open(result_file, "r") as f:
                result = json.load(f)
        else:
            # read results from Ansys output
            with open(result_file, "r") as f:
                reader = csv.reader(f, delimiter=",")
                result_keys = next(reader)
                result_values = next(reader)
                result = {k[:-3]: float(v) for k, v in zip(result_keys, result_values)}

        energy = {k[2:]: v for k, v in result.items() if k.startswith("E_")}
        total_energy = result.get("total_energy", sum(energy.values()))
        if total_energy == 0.0:
            continue

        loss = {
            loss_layer: sum([loss * v / total_energy for k, v in energy.items() if loss_layer in k])
            for loss_layer, loss in loss_tangents.items()
        }
        q[key] = {"Q_" + k: (1.0 / v if v else float("inf")) for k, v in loss.items()}
        q[key]["Q_total"] = 1.0 / sum(loss.values())

    tabulate_into_csv(f"{os.path.basename(os.path.abspath(path))}_q_factors.csv", q, parameters, parameter_values)
