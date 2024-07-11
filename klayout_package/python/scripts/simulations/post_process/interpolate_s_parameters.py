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
Interpolates an existing touchstone (.sNp) file

Args:
    sys.argv[1]: json file containing
        - "frequencies": list of frequencies where to interpolate at
        - "simulated_snp": (Optional) filename for the input data used in the interpolation

If no "simulated_snp" is set the input snp will be searched in the folder first based on the names of
`project_results.json` files and then by pattern matching `.sNp` file extension. Interpolation is done separately
for each input snp found.

The result file will be named similarly to the input snp, but with an added `_interpolated` suffix (before extension)
"""
import json
import os
import sys

from interpolating_frequency_sweep import interpolate_s_parameters_from_snp


def _snp_extension(f):
    ending = f.rpartition(".s")[2]
    return ending.endswith("p") and ending[:-1].isdigit()


def _get_port_num(def_file):
    with open(def_file, "r") as f:
        data = json.load(f)
    return len(data["ports"])


if len(sys.argv) > 1:
    with open(sys.argv[1], "r") as fp:
        pp_data = json.load(fp)
else:
    raise RuntimeError("Not enough arguments given to interpolate_s_parameters: Need filename of post_process json")

freqs = pp_data["frequencies"]

if "simulated_snp" in pp_data:
    snp_files = [pp_data["simulated_snp"]]
else:
    # Find name from json
    path = os.path.curdir
    result_files = [f for f in os.listdir(path) if f.endswith("_project_results.json")]
    definition_files = [f.replace("_project_results.json", ".json") for f in result_files]
    snp_files = [f.replace(".json", f".s{_get_port_num(f)}p") for f in definition_files]

snp_files = [f for f in snp_files if os.path.isfile(f)]

# If not found just search based on extension
if not snp_files:
    snp_files = [f for f in os.listdir(path) if _snp_extension(f) and "_interpolated" not in f]

if not snp_files:
    raise RuntimeError("Found no sNp files in interpolate_s_parameters")

result_folder = "s_matrix_plots"
if not os.path.exists(result_folder):
    os.mkdir(result_folder)


for snp in snp_files:
    part_snp = list(snp.rpartition(".s"))
    part_snp[0] = part_snp[0] + "_interpolated"
    interpolate_s_parameters_from_snp(snp, "".join(part_snp), freqs, plot_results=True, image_folder=result_folder)
