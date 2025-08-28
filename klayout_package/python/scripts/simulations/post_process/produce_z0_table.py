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
Produce table containing waveguide parameters Cs, Ls, and Z0 terms from cross section results
"""

import os
from math import sqrt
from post_process_helpers import find_varied_parameters, tabulate_into_csv, load_json

# Find data files
path = os.path.curdir
result_files = [f for f in os.listdir(path) if f.endswith("_project_results.json")]
if result_files:
    # Find parameters that are swept
    definition_files = [f.replace("_project_results.json", ".json") for f in result_files]
    parameters, parameter_values = find_varied_parameters(definition_files)

    # Load result data
    matrix = {}
    for key, result_file in zip(parameter_values.keys(), result_files):
        result = load_json(result_file)
        cs = result.get("Cs")
        ls = result.get("Ls")
        if not (cs and ls):
            print(f"'Cs' and/or 'Ls' not found in the result file {result_file}")
            continue
        matrix[key] = {"Cs": cs[0][0], "Ls": ls[0][0], "Z0": sqrt(ls[0][0] / cs[0][0])}

    tabulate_into_csv(f"{os.path.basename(os.path.abspath(path))}_Z0.csv", matrix, parameters, parameter_values)
