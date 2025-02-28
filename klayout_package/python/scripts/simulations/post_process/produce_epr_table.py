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

pp_data = {}
if len(sys.argv) > 1:
    with open(sys.argv[1], "r", encoding="utf-8") as fp:
        pp_data = json.load(fp)

groups = pp_data.get("groups", [])
region_corrections = pp_data.get("region_corrections", {})
deembed_lens = pp_data.get("deembed_lens", [])
deembed_cross_sections = pp_data.get("deembed_cross_sections", [])
deembed = deembed_cross_sections and deembed_lens


def _get_ith(d: list | tuple | float, i: int):
    """gets the ith element of a list that also works for scalars"""
    return d[i] if isinstance(d, (list, tuple)) else d


def excitation_list(json_data: dict):
    """Excitation indices in ascending order (excludes ground, excitation 0)"""
    return sorted(set(l["excitation"] for _, l in json_data["layers"].items() if "excitation" in l) - {0})


def get_ind_by_exc(simulation: str, excitation: int):
    with open(f"{simulation}.json", "r", encoding="utf-8") as f:
        sim_data = json.load(f)

    excitations = excitation_list(sim_data)
    return excitations.index(excitation) if excitation in excitations else 0


def get_mer_coefficients(simulation: str, region: str, excitation: int):
    """
    Returns the MER correction coefficients, i.e., EPRs from the 2D cross-section simulation normalized within MER.
    Groups the EPRs according to the global variable `groups`

    Args:
        simulation: Simulation name
        region:     Name of the partition region
        excitation: signal excitation for the 3D result

    Returns:
        Dictionary containing EPRs in metal-edge-region for each group
    """
    correction_key = region_corrections.get(region)
    if correction_key is None:
        return None

    cs_name = simulation + "_" + correction_key

    with open(f"{cs_name}_project_results.json", "r", encoding="utf-8") as f:
        res = json.load(f)

    result_ind = get_ind_by_exc(cs_name, excitation)

    mer_keys = [k for k, _ in res.items() if "mer" in k and k.startswith("E_")]

    mer_total = sum(_get_ith(res[k], result_ind) for k in mer_keys)
    if mer_total == 0:
        print(f'Total energy 0 for correction of region "{region}" in "{simulation}"')
        mer_total = float("inf")

    coefficient = {
        group: sum(_get_ith(res[k], result_ind) for k in mer_keys if group.lower() in k.lower()) / mer_total
        for group in groups
    }

    return coefficient


def get_deembed_p_dict(simulation: str, region: str, deembed_len: float, total_energy: float, excitation: int):
    """
    Returns the 3D EPRs of a cross-section simulation extruded to having a length `deembed_len` and
    normalized by `total energy`. Can be used to deembed the effect of the region in post-processsings.

    Groups the EPRs according to the global variable `groups`

    Args:
        simulation:   Simulation name
        region:       Name of the partition region
        deembed_len:  Length of the deembedding in micrometers
        total_energy: Total energy of the 3D simulation
        excitation:   signal excitation for the 3D result

    Returns:
        Dictionary containing the EPRs for each group
    """
    correction_key = region_corrections.get(region)
    if correction_key is None:
        return None

    cs_name = simulation + "_" + correction_key

    with open(f"{cs_name}_project_results.json", "r", encoding="utf-8") as f:
        res = json.load(f)

    result_ind = get_ind_by_exc(cs_name, excitation)

    energy_keys = [k for k, _ in res.items() if k.startswith("E_")]
    e_scale = deembed_len * 1e-6  # um scale
    deembed_dict = {
        f"p_{group}": e_scale
        * sum(_get_ith(res[k], result_ind) for k in energy_keys if group.lower() in k.lower())
        / total_energy
        for group in groups
    }

    return deembed_dict


def get_results_list(results: dict[str, list[float] | float]):
    """Transforms a single dictionary with list values to a list of dictionaries with scalar values"""
    energy_results = {
        k: v for k, v in results.items() if k.startswith("E_") or k.startswith("Exy_") or k.startswith("Ez_")
    }
    if not energy_results:
        return []

    num_results_list = [len(v) if isinstance(v, (list, tuple)) else 1 for _, v in energy_results.items()]
    num_results = min(num_results_list)
    if any((n != num_results for n in num_results_list)):
        print(f"Varying number of energy results in project_results.json. Will only use the first {num_results}")

    results_list = []
    for result_i in range(num_results):
        results_list.append({k: _get_ith(v, result_i) for k, v in energy_results.items()})

    return results_list


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
    parameters = ["result_index"] + parameters

    # Load result data
    epr_dict = {}
    for i, (original_key, result_file) in enumerate(zip(list(parameter_values.keys()), result_files)):
        with open(result_file, "r", encoding="utf-8") as f:
            result_json = json.load(f)
        with open(f"{original_key}.json", "r", encoding="utf-8") as f:
            sim_data = json.load(f)

        results_list = get_results_list(result_json)
        if not results_list:
            print(f'No energy results found in "{result_file}".')

        original_params = parameter_values.pop(original_key)
        for excitation, result in zip(excitation_list(sim_data), results_list):
            energy = {k[2:]: v for k, v in result.items() if k.startswith("E_")}

            # Add result index if we have multiple results
            key = original_key + ("_" + str(excitation) if len(results_list) > 1 else "")
            # duplicate params for each result in the json and add the result index
            parameter_values[key] = [excitation] + original_params

            def _sum_value(_dict, _key, _addition):
                _dict[_key] = _dict.get(_key, 0.0) + _addition

            # add sheet energies if 'sheet_approximations' are available
            if "sheet_approximations" in pp_data:
                xy_energy = {k[4:]: v for k, v in result.items() if k.startswith("Exy_")}
                z_energy = {k[3:]: v for k, v in result.items() if k.startswith("Ez_")}

                # read layers and material_dict data to determine sheet background materials
                sheet_layers = [(k, d) for k, d in sim_data["layers"].items() if k in xy_energy or k in z_energy]
                eps_r_dict = {k: d["permittivity"] for k, d in sim_data["material_dict"].items() if "permittivity" in d}
                bg_key = {k: d.get("background", "unknown_sheet_background") for k, d in sheet_layers}
                bg_eps_r = {k: eps_r_dict.get(d.get("material"), 1.0) for k, d in sheet_layers}

                for k, d in pp_data["sheet_approximations"].items():
                    if "thickness" not in d:
                        print(f'"thickness" missing from sheet_approximations["{k}"]')
                        continue
                    eps_r = d["eps_r"]

                    for xy_k, xy_v in xy_energy.items():
                        if k in xy_k:
                            _sum_value(energy, xy_k, xy_v * d["thickness"] * eps_r)
                            _sum_value(energy, bg_key[xy_k], -xy_v * d["thickness"] * bg_eps_r[xy_k])

                    for z_k, z_v in z_energy.items():
                        if k in z_k:
                            _sum_value(energy, z_k, z_v * d["thickness"] * (bg_eps_r[z_k] ** 2) / eps_r)
                            _sum_value(energy, bg_key[z_k], -z_v * d["thickness"] * bg_eps_r[z_k])

            elif any(k.startswith("Exy_") or k.startswith("Ez_") for k in result.keys()):
                print(
                    'Results contain boundary energies, but no "sheet_approximation" is defined. ',
                    "Boundary energies will be ignored in EPR",
                )

            total_energy = sum(energy.values())
            if total_energy == 0.0:
                print(f'Total energy 0 for simulation "{key}". No EPRs will be written.')
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
                epr_dict[key] = {}
                for reg, corr in region_corrections.items():
                    reg_energy = {k: v for k, v in energy.items() if reg in k}

                    coefficients = get_mer_coefficients(original_key, reg, excitation)
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
            if deembed:

                def is_port_excited(original_key, deembed_cs, excitation):
                    with open(f"{original_key}_{deembed_cs}.json", "r", encoding="utf-8") as f:
                        cs_data = json.load(f)
                    if cs_data.get("voltage_excitations"):
                        return True
                    return any(v.get("excitation") == excitation for v in cs_data["layers"].values())

                sim_name = sim_data["simulation_name"]
                if sim_name not in deembed_lens:
                    print("`deembed_lens` not found in correction.json, something might not work correctly!")
                if sim_name not in deembed_cross_sections:
                    print("`deembed_cross_sections` not found in correction.json, something might not work correctly!")
                deembed_len_list = deembed_lens[sim_name]
                deembed_cross_section_list = deembed_cross_sections[sim_name]
                for deembed_len, deembed_cs in zip(deembed_len_list, deembed_cross_section_list):
                    deembed_dict = get_deembed_p_dict(original_key, deembed_cs, deembed_len, total_energy, excitation)
                    port_excited = is_port_excited(original_key, deembed_cs, excitation)
                    for k, v in deembed_dict.items():
                        epr_dict[key][f"deembed_{k}_{deembed_cs}"] = v * port_excited

                for group in groups:
                    epr_dict[key][f"deembed_p_{group}"] = sum(
                        v for k, v in epr_dict[key].items() if k.startswith(f"deembed_p_{group}")
                    )

            epr_dict[key]["E_total"] = total_energy

    tabulate_into_csv(f"{os.path.basename(os.path.abspath(path))}_epr.csv", epr_dict, parameters, parameter_values)
