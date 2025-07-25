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
Post process script to extract solution field values from Elmer simulation results at given points.

Requires the full result of a completed Elmer simulation, which can be saved using solution option `save_elmer_data`

By default extracts fields for all coordinate files ending in `_tls_mc.json` found in the current folder.
These files can be generated by running `tls_monte_carlo_points.py` before this script.

An example usage of the TLS monte carlo sampler and this field extractor script can be found in
`scripts/simulations/tls_waveguide_sim_elmer.py`
"""
import logging
from pathlib import Path
import sys
import json
import pandas as pd
import numpy as np
from elmer_helpers import (
    sif_common_header,
    sif_block,
    read_mesh_names,
    get_layer_list,
    get_save_data_solver,
    read_elmer_results,
    get_electrostatics_solver,
)
from run_helpers import _run_elmer_solver


def get_data_extraction_sif(
    json_data: dict,
    elmer_data_file: str,
    results_file: str,
    points_list: list[dict[str, float]],
    restart_position: int = 1,
):
    """
    Get contents of Elmer solver input file (.sif) used for extracting the field data

    Embeds the requested point coordinates `points_list` in the .sif
    """
    dim = 2 if json_data["tool"] == "cross-section" else 3

    if dim != len(points_list[0]):
        logging.warning("Sampled coordinate dimensions and json dimensions do not match")
        sys.exit()

    header = sif_common_header(
        json_data,
        json_data["name"],
        json_data["mesh_name"],
        def_file=None,  # Could we use this to load the points
        dim=dim,
        constraint_modes_analysis=False,
        restart_file=elmer_data_file,
        restart_position=restart_position,
    )
    unit = 1e-6
    points_list = [[unit * vd["x"], unit * vd["y"]] + ([unit * vd["z"]] if dim == 3 else []) for vd in points_list]

    # We do not run this solver, but need it for Elmer to correctly load the elemental field data
    solver = get_electrostatics_solver(json_data, 1, "f.dat", c_matrix_output=False, exec_solver="Never")

    solver += get_save_data_solver(2, result_file=results_file, save_coordinates=points_list)

    placeholders = sif_block("Equation 1", ["Active Solvers(1) = 1"])
    placeholders += sif_block("Boundary Condition 1", [" Target Boundaries(0) = "])

    mesh_bodies, _ = read_mesh_names(Path(json_data["mesh_name"]))
    sif_bodies = get_layer_list(json_data, mesh_bodies)
    placeholders += "".join(
        [sif_block(f"Body {i}", [f"Target Bodies(1) = $ {b}", "Equation = 1"]) for i, b in enumerate(sif_bodies, 1)]
    )

    return header + solver + placeholders


def get_elmer_results(path: str | Path, tmp_results_file: str):
    """
    Reads the Elmer result data found in `path/tmp_results_file`.

    Reshapes the result of shape (N_points * M, 1) where M is the number of field values at each point to a dataframe
    with shape (N_points, M)

    Ignores the prefix `eigen` in result variable names
    """
    df = read_elmer_results(Path(path) / tmp_results_file)

    data_keys = []
    for col in df.keys():
        new_key = (col.partition("value: ")[2]).partition(" in element")[0]
        new_key = new_key[len("eigen 1 ") :] if new_key.startswith("eigen ") else new_key
        # take only unique keys and assume the order remains the same
        if new_key in data_keys:
            break
        data_keys.append(new_key)

    nrows, ncols = df.values.shape
    nkeys = len(data_keys)
    if ncols % nkeys != 0:
        logging.warning(f"Number of columns is not divisible by the number of unique keys found in {tmp_results_file}")
    if nrows > 1:
        logging.warning(f"Incorrect data shape in {tmp_results_file}. Expected a single row.")

    # rename columns `coordinate 1` -> `x` and `electric field 1` -> `E_x`

    col_map = {}
    for i, coord in enumerate(["x", "y", "z"], 1):
        col_map.update(
            {f"coordinate {i}": coord, f"electric field {i}": "E_" + coord, f"electric field e {i}": "E_" + coord}
        )
    data_keys = [col_map.get(k, k) for k in data_keys]
    return pd.DataFrame(columns=data_keys, data=np.reshape(df.values, (int(ncols / nkeys), nkeys)))


#############################
#       MAIN SCRIPT         #
#############################

# Find data files
tls_files = list(Path("").glob("*_tls_mc.json"))
if not tls_files:
    logging.warning("No sample point files ending with `_tls_mc.json` found.")
    sys.exit()

for tls_file in tls_files:
    def_file = str(tls_file).removesuffix("_tls_mc.json") + ".json"

    if not Path(def_file).exists():
        logging.warning(f'Simulation definition file "{def_file}" not found')
        continue

    with open(def_file, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    sim_folder = json_data["name"]  # should be same as the json name
    elmer_data_file = f"{sim_folder}.result"
    if next(Path(sim_folder).glob(f"{elmer_data_file}*"), None) is None:
        logging.warning(
            f'Elmer model data "{elmer_data_file}" not found.\n'
            "Make sure the simulation is exported and run with the solution option `save_elmer_data=True`"
        )
        continue

    with open(tls_file, "r", encoding="utf-8") as f:
        tls_data = json.load(f)

    elmer_partitions = json_data["workflow"].get("sbatch_parameters", json_data["workflow"]).get("elmer_n_processes", 1)
    # save in csv instead of json
    final_result_filename = f"{sim_folder}_fields.csv"
    df_list = []

    if json_data.get("voltage_excitations"):
        excitations = [1]
    else:
        excitations = sorted(set(l["excitation"] for _, l in json_data["layers"].items() if "excitation" in l) - {0})
    for face, face_data in tls_data.items():
        if face == "metadata":
            continue
        for layer, values in face_data.items():
            if not values:
                continue
            for exc in excitations:
                tmp_results_file = f"fields_{layer}_{face}_{exc}.dat"
                sif_filename = f"field_extractor_{layer}_{face}_{exc}"
                sif_contents = get_data_extraction_sif(
                    json_data, elmer_data_file, tmp_results_file, values, restart_position=exc
                )
                with open(Path(sim_folder) / f"{sif_filename}.sif", "w", encoding="utf-8") as f:
                    f.write(sif_contents)

                _run_elmer_solver(sim_folder, [sif_filename], 1, elmer_partitions, 1)

                df_layer = get_elmer_results(sim_folder, tmp_results_file)
                if df_layer is None:
                    continue

                df_layer["excitation"] = exc
                df_layer["face"] = face
                df_layer["layer"] = layer
                df_layer["E_abs"] = np.sqrt(
                    np.square(df_layer["E_x"]) + np.square(df_layer["E_y"]) + np.square(df_layer.get("E_z", 0))
                )
                df_list.append(df_layer)

    pd.concat(df_list).to_csv(final_result_filename)
