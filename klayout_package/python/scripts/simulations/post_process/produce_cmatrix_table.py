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
"""
Produces cmatrix table from Ansys or Elmer results

Produces deembed capacitances if `deembed_cross_sections` is set in the simulations class and corresponding
cross-section simulation results are found.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "util"))
from post_process_helpers import (  # pylint: disable=wrong-import-position, no-name-in-module
    find_varied_parameters,
    tabulate_into_csv,
    load_json,
)


def _get_excitations(json_data):
    return {l["excitation"] for l in json_data["layers"].values() if l.get("excitation", 0) > 0}


# Find data files
path = os.path.curdir
result_files = [f for f in os.listdir(path) if f.endswith("_project_results.json")]
if result_files:
    # Find parameters that are swept
    definition_files = [f.replace("_project_results.json", ".json") for f in result_files]
    parameters, parameter_values = find_varied_parameters(definition_files)

    # Load result data
    cmatrix = {}
    for key, result_file in zip(parameter_values.keys(), result_files):
        result = load_json(result_file)
        cdata = result.get("CMatrix") or result.get("Cs")
        if cdata is None:
            print(f"Neither 'CMatrix' nor 'Cs' found in the result file {result_file}")
            continue

        cmatrix[key] = {f"C{i+1}{j+1}": c for i, l in enumerate(cdata) for j, c in enumerate(l)}

    # deembedding
    try:
        def_data_cs = {}
        def_data_3d = {}
        for key, def_file in zip(parameter_values.keys(), definition_files):
            data = load_json(def_file)
            (def_data_cs if data["tool"] == "cross-section" else def_data_3d)[key] = data

        for key, def_data in def_data_3d.items():
            for port in def_data.get("ports", []):
                d_len, d_cross_section = 1e-6 * port.get("deembed_len", 0), port.get("deembed_cross_section")
                if d_len and d_cross_section:
                    cs_key = f"{key}_{d_cross_section}"
                    if cs_key not in def_data_cs:
                        print(f"WARNING: deembed cross section not found {cs_key}")
                        continue
                    exc_set = _get_excitations(def_data_cs[cs_key])
                    if len(exc_set) > 1:
                        print(f"WARNING: Multiple signals in deembedding cross section {cs_key}")
                        continue
                    exc = exc_set.pop()
                    deembed_key = f"C{exc}{exc}_deembed"
                    deembed_c = d_len * cmatrix[cs_key]["C11"]
                    cmatrix[key][deembed_key] = cmatrix[key].get(deembed_key, 0) + deembed_c
                    cmatrix[key][f"C{exc}{exc}"] -= deembed_c

    except Exception as e:  # pylint: disable=broad-except
        print(f"Encountered exception in capacitance deembedding\n {e}")

    tabulate_into_csv(f"{os.path.basename(os.path.abspath(path))}_results.csv", cmatrix, parameters, parameter_values)
