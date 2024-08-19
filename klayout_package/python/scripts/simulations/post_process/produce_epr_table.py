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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).
"""
Produces EPR table from Ansys or Elmer results

Args:
    sys.argv[1]: parameter file for EPR calculations. Can include following:
    - sheet_approximations: dictionary to transform sheet integral to thin layer integral. Includes parameters for
        thickness, eps_r, and background_eps_r
    - groups: List of layer keys. If given, the layers including a key are grouped together and other layers are ignored
    - region_corrections: Dictionary with partition region names as keys and EPR correction keys as values.
        If given, the script tries to look for cross-section results for EPR correction and groups EPRs by partition
        region names.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "util"))
from post_process_helpers import (  # pylint: disable=wrong-import-position, no-name-in-module
    find_varied_parameters,
    tabulate_into_csv,
)

pp_data = dict()
if len(sys.argv) > 1:
    with open(sys.argv[1], "r") as fp:
        pp_data = json.load(fp)

groups = pp_data.get("groups", [])
region_corrections = pp_data.get("region_corrections", dict())


def get_mer_coefficients(simulation, region):
    """
    returns the MER coefficients for certain path and saves the loaded coefficients in a separate json file.

    Args:
        simulation(String): Simulation key
        region(String): Name of the partition region

    Returns:
        Dictionary containing EPRs in metal-edge-region for each group

    """
    correction_key = region_corrections.get(region)
    if correction_key is None:
        return None

    corr_key = "_" + correction_key
    corr_file = {f for f in correction_files if corr_key in f and simulation.startswith(f[: f.find(corr_key)])}
    if not corr_file:
        print(f"Expected correction file not found with keys {simulation} and {correction_key}.")
        return None
    if len(corr_file) > 1:
        print(f"Multiple matching correction files found with keys {simulation} and {correction_key}.")
        return None

    with open(corr_file.pop(), "r") as f:
        res = json.load(f)
    mer_keys = [k for k, v in res.items() if "mer" in k and k.startswith("E_")]
    mer_total = sum([res[k] for k in mer_keys])
    coefficient = {group: sum(res[k] for k in mer_keys if group.lower() in k.lower()) / mer_total for group in groups}

    with open(f"coefficients_{simulation}_{region}.json", "w") as f:
        json.dump(coefficient, f)

    return coefficient


# Find data files
path = os.path.curdir
all_files = [f for f in os.listdir(path) if f.endswith("_project_results.json")]
correction_keys = {k for k in region_corrections.values() if k is not None}
correction_files = [f for f in all_files if any(k in f for k in correction_keys)]
result_files = list(set(all_files) - set(correction_files))

if result_files:
    # Find parameters that are swept
    definition_files = [f.replace("_project_results.json", ".json") for f in result_files]
    parameters, parameter_values = find_varied_parameters(definition_files)

    # Load result data
    epr_dict = {}
    for key, result_file in zip(parameter_values.keys(), result_files):
        with open(result_file, "r") as f:
            result = json.load(f)

        energy = {k[2:]: v for k, v in result.items() if k.startswith("E_")}

        # add sheet energies if 'sheet_approximations' are available
        if "sheet_approximations" in pp_data:
            xy_energy = {k[4:]: v for k, v in result.items() if k.startswith("Exy_")}
            z_energy = {k[3:]: v for k, v in result.items() if k.startswith("Ez_")}
            for k, d in pp_data["sheet_approximations"].items():
                if "thickness" not in d:
                    continue
                eps_r = d.get("eps_r", 1.0)
                xy_scale = d["thickness"] * eps_r
                for xy_k, xy_v in xy_energy.items():
                    if k in xy_k:
                        energy[xy_k] = energy.get(xy_k, 0.0) + xy_scale * xy_v
                background_eps_r = d.get("background_eps_r", 1.0)
                z_scale = d["thickness"] * background_eps_r * background_eps_r / eps_r
                for z_k, z_v in z_energy.items():
                    if k in z_k:
                        energy[z_k] = energy.get(z_k, 0.0) + z_scale * z_v

        total_energy = sum(energy.values())
        if total_energy == 0.0:
            continue

        if not groups:
            # calculate EPR corresponding to each energy integral
            epr_dict[key] = {f"p_{k}": v / total_energy for k, v in energy.items()}
        elif not region_corrections:
            # use EPR groups to combine layers
            epr_dict[key] = {
                f"p_{group}": sum(v for k, v in energy.items() if group in k) / total_energy for group in groups
            }
        else:
            # calculate corrected EPRs and distinguish by partition regions
            epr_dict[key] = dict()
            for reg, corr in region_corrections.items():
                reg_energy = {k: v for k, v in energy.items() if reg in k}

                coefficients = get_mer_coefficients(key, reg)
                if coefficients is None:
                    epr_dict[key].update(
                        {
                            f"p_{group}_{reg}": sum(v for k, v in reg_energy.items() if group in k) / total_energy
                            for group in groups
                        }
                    )
                else:
                    epr_dict[key].update(
                        {
                            f"p_{group}_{reg}": coefficients[group] * sum(reg_energy.values()) / total_energy
                            for group in groups
                        }
                    )

            # distinguish regions not included in region_corrections with 'default' key
            def_energy = {k: v for k, v in energy.items() if all(reg not in k for reg in region_corrections.keys())}
            epr_dict[key].update(
                {
                    f"p_{group}_default": sum(v for k, v in def_energy.items() if group in k) / total_energy
                    for group in groups
                }
            )

            # total EPR by groups
            epr_dict[key].update(
                {f"p_{group}": sum(v for k, v in epr_dict[key].items() if group in k) for group in groups}
            )

    tabulate_into_csv(f"{os.path.basename(os.path.abspath(path))}_epr.csv", epr_dict, parameters, parameter_values)
