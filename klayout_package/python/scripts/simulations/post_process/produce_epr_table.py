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

    with open(corr_file.pop(), "r", encoding="utf-8") as f:
        res = json.load(f)
    mer_keys = [k for k, v in res.items() if "mer" in k and k.startswith("E_")]
    mer_total = sum(res[k] for k in mer_keys)
    coefficient = {group: sum(res[k] for k in mer_keys if group.lower() in k.lower()) / mer_total for group in groups}

    with open(f"coefficients_{simulation}_{region}.json", "w", encoding="utf-8") as f:
        json.dump(coefficient, f)

    return coefficient


def _get_face_id_to_substrate_mapping(sim_name: str) -> dict[str, str]:
    """
    Returns a dictionary that maps a given face id to the correspond substrate layer

    Mapping is based on the value of `face_stack` from the simulation json and available substrate layers
    """
    with open(f"{sim_name}.json", "r", encoding="utf-8") as f:
        sim_data = json.load(f)
    face_stack = sim_data["parameters"]["face_stack"]

    def _to_list(x):
        return x if isinstance(x, list) else [x]

    # make into a 2D list
    face_stack = [_to_list(flist) for flist in face_stack]

    if len(face_stack) == 1:
        mapping = {f: "substrate_1" for f in face_stack[0]}
    else:
        if any(h == 0 for h in _to_list(sim_data["parameters"]["substrate_height"])):
            print("WARNING: Using substrate height 0.0 not supported with EPR sheet approximations")
            return None

        lower_box_height = sim_data["parameters"]["lower_box_height"]
        mapping = {}

        # This should give a mapping to substrate indices
        # if lower_box_height==0 [1,2,2,3,3... ]
        # else                   [1,1,2,2,3,...]
        for ind, flist in enumerate(face_stack, 3 if lower_box_height == 0 else 2):
            mapping.update({f: f"substrate_{ind//2}" for f in flist})

    # As a sanity check compare the available substrate layers and the indices used in mapping and
    # Assume that the substrate numbering does not go over 9
    substrate_layers = [l[:11] for l in sim_data["layers"].keys() if l.startswith("substrate_")]
    if set(substrate_layers) != set(mapping.values()):
        print("Substrate layers based on face_stack do not match the ones found in layers dict.")
        print(f"Layers: {set(substrate_layers)}. Face_stack: {set(mapping.values())}")
        print("Bulk EPR correction will be saved as negative values in separate layers")
        return None

    return mapping


def _get_partition_region_names(sim_name: str) -> list[str]:
    """Read partition region names from simulation json file"""
    with open(f"{sim_name}.json", "r", encoding="utf-8") as f:
        sim_data = json.load(f)
    return [p["name"] for p in sim_data["parameters"]["partition_regions"]]


def _get_bg_key(
    if_layer: str, correction_key: str, bg_eps_r: float, layer_mapping: dict[str, str], regions: list[str]
) -> str:
    """
    Get background layer name for correcting its energy in sheet approximation applied to "if_layer"

    Args:
        if_layer: Interface layer name
        correction_key: Corresponding key of the sheet approximation dictionary, should be substring of "if_layer"
        bg_eps_r: Relative permittivity of the background layer
        layer_mapping: Mapping from face_ids to substrate layers, obtained with "_get_face_id_to_substrate_mapping"
        regions: Partition region names

    Returns:
        Background layer name
    """
    face_id = if_layer.partition("_")[0]

    if bg_eps_r != 1.0 and layer_mapping is None:
        return "bulk_corr" + if_layer

    basename = "vacuum" if bg_eps_r == 1.0 else layer_mapping[face_id]

    region = if_layer.partition(correction_key)[2]

    if len(region) > 0 and region not in regions:
        matches = [r for r in regions if region.endswith(r)]
        if len(matches) != 1:
            print(f"Too many or no matching regions found: {matches}")
            return "bulk_corr" + if_layer

        region = matches[0]

    return basename + region


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
        with open(result_file, "r", encoding="utf-8") as f:
            result = json.load(f)

        energy = {k[2:]: v for k, v in result.items() if k.startswith("E_")}

        def _add_energy(e_dict, key, ene):
            e_dict[key] = e_dict.get(key, 0.0) + ene

        # add sheet energies if 'sheet_approximations' are available
        if "sheet_approximations" in pp_data:
            xy_energy = {k[4:]: v for k, v in result.items() if k.startswith("Exy_")}
            z_energy = {k[3:]: v for k, v in result.items() if k.startswith("Ez_")}

            bg_substrate_mapping = _get_face_id_to_substrate_mapping(key)
            region_names = _get_partition_region_names(key)

            for k, d in pp_data["sheet_approximations"].items():
                if "thickness" not in d:
                    print(f'"thickness" missing from sheet_approximations["{k}"]')
                    continue
                eps_r = d["eps_r"]
                xy_scale = d["thickness"] * eps_r
                background_eps_r = d["background_eps_r"]
                bg_scale = d["thickness"] * background_eps_r

                for xy_k, xy_v in xy_energy.items():
                    if k in xy_k:
                        _add_energy(energy, xy_k, xy_scale * xy_v)
                        bg_key = _get_bg_key(xy_k, k, background_eps_r, bg_substrate_mapping, region_names)
                        _add_energy(energy, bg_key, -bg_scale * xy_v)

                z_scale = d["thickness"] * background_eps_r * background_eps_r / eps_r
                for z_k, z_v in z_energy.items():
                    if k in z_k:
                        _add_energy(energy, z_k, z_scale * z_v)
                        bg_key = _get_bg_key(z_k, k, background_eps_r, bg_substrate_mapping, region_names)
                        _add_energy(energy, bg_key, -bg_scale * z_v)

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

        epr_dict[key]["E_total"] = total_energy

    tabulate_into_csv(f"{os.path.basename(os.path.abspath(path))}_epr.csv", epr_dict, parameters, parameter_values)
