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
Produces quality factor table from Ansys or Elmer results. Depends on `produce_epr_table.py` which should be run
before this script. If `groups` argument was provided to `produce_epr_table.py`, the same groups should be used as
keys in the loss tangents dictionary provided to this script.

Args:
    sys.argv[1]: parameter file name, where the file includes loss tangents for different layers

"""
import sys
import subprocess
import logging
from pathlib import Path
import pandas as pd
from post_process_helpers import find_varied_parameters, load_json

loss_tangents = load_json(sys.argv[1])

epr_files = list(Path(".").glob("*_epr.csv"))
def_files = [str(p).replace("_project_results.json", ".json") for p in Path(".").glob("*_project_results.json")]
sweep_params, _ = find_varied_parameters(def_files)

if not epr_files:
    # If the result contains sheet energies, produce_epr_table will print a warning
    # and this script will crash later to key error due to missing ma, ms, sa
    logging.warning("EPR results not found. Running `produce_epr_table.py` without input arguments.")
    ret = subprocess.call("python scripts/produce_epr_table.py", shell=True)
    if ret != 0:
        sys.exit()
    epr_files = list(Path(".").glob("*_epr.csv"))


def _sum_losses(epr_df, epr_keys, loss_key, loss_value):
    matches = [epr_df[epr_k] for epr_k in epr_keys if loss_key in epr_k]
    if not matches:
        logging.warning(f"No matching EPR layer names found for loss tangent key '{loss_key}'")
    return sum(matches) * loss_value


for epr_file in epr_files:
    epr_df = pd.read_csv(epr_file)
    epr_keys = ["E_total"] + [k for k in epr_df.keys() if k.startswith("p_") and k not in sweep_params]
    # if the loss tangent layer keys are found exactly as p_{key} in the epr csv
    # They are used directly. Otherwise all layer EPRs which contain `key` are summed
    if all((f"p_{k}" in epr_keys for k in loss_tangents.keys())):
        loss_df = pd.DataFrame({k: epr_df[f"p_{k}"] * v for k, v in loss_tangents.items()})
    else:
        loss_df = pd.DataFrame({k: _sum_losses(epr_df, epr_keys, k, v) for k, v in loss_tangents.items()})

    for k, v in loss_df.items():
        epr_df[f"Q_{k}"] = 1 / v

    epr_df["Q_total"] = 1 / loss_df.sum(axis=1)

    epr_df = epr_df.drop(columns=epr_keys)

    epr_df.to_csv(str(epr_file).replace("_epr.csv", "_q_factors.csv"))
