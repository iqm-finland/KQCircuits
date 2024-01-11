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
Produces EPR table from Ansys or Elmer results

Args:
    sys.argv[1]: parameter file for EPR calculations. Can include following:
    - sheet_approximations: dictionary to transform sheet integral to thin layer integral. Includes parameters for
        thickness, eps_r, and background_eps_r
    - groups: List of layer keys. If given, the layers including a key are grouped together and other layers are ignored
    - mer_correction_path: If given, the script tries to look for Elmer cross-section results for EPR correction
"""
import json
import os
import sys
import csv
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'util'))
from post_process_helpers import find_varied_parameters, tabulate_into_csv \
    # pylint: disable=wrong-import-position, no-name-in-module

pp_data = dict()
if len(sys.argv) > 1:
    with open(sys.argv[1], 'r') as fp:
        pp_data = json.load(fp)

# Find data files
path = os.path.curdir
result_files = [f for f in os.listdir(path) if f.endswith('_project_energy.csv') or f.endswith('_result.json')]
if result_files:
    # Find parameters that are swept
    definition_files = [f.replace('_result.json', '.json') if f.endswith('_result.json') else
                        f.replace('_project_energy.csv', '.json') for f in result_files]
    parameters, parameter_values = find_varied_parameters(definition_files)

    # Load result data
    epr_dict = {}
    for key, result_file in zip(parameter_values.keys(), result_files):
        if result_file.endswith('_result.json'):
            # read results from Elmer output
            with open(result_file, 'r') as f:
                result = json.load(f)
        else:
            # read results from Ansys output
            with open(result_file, 'r') as f:
                reader = csv.reader(f, delimiter=',')
                result_keys = next(reader)
                result_values = next(reader)
                result = {k[:-3]: float(v) for k, v in zip(result_keys, result_values)}

        energy = {k[2:]: v for k, v in result.items() if k.startswith("E_")}

        # add sheet energies if 'sheet_approximations' are available
        if 'sheet_approximations' in pp_data:
            xy_energy = {k[4:]: v for k, v in result.items() if k.startswith("Exy_")}
            z_energy = {k[3:]: v for k, v in result.items() if k.startswith("Ez_")}
            for k, d in pp_data['sheet_approximations'].items():
                if 'thickness' not in d:
                    continue
                eps_r = d.get('eps_r', 1.0)
                xy_scale = d['thickness'] * eps_r
                for xy_k, xy_v in xy_energy.items():
                    if k in xy_k:
                        energy[xy_k] = energy.get(xy_k, 0.0) + xy_scale * xy_v
                background_eps_r = d.get('background_eps_r', 1.0)
                z_scale = d['thickness'] * background_eps_r * background_eps_r / eps_r
                for z_k, z_v in z_energy.items():
                    if k in z_k:
                        energy[z_k] = energy.get(z_k, 0.0) + z_scale * z_v

        total_energy = sum(energy.values())
        if total_energy == 0.0:
            continue

        if 'groups' not in pp_data:
            # calculate EPR corresponding to each energy integral
            epr_dict[key] = {"p_" + k: v / total_energy for k, v in energy.items()}
        elif 'mer_correction_path' not in pp_data:
            # use EPR groups to combine layers
            epr_dict[key] = {"p_" + group: sum([v / total_energy for k, v in energy.items() if group in k])
                             for group in pp_data['groups']}
        else:
            # distinguish EPRs to mer and nonmer groups and calculate corrected EPRs
            mer_coefficients = dict()
            full_mer_path = Path(pp_data['mer_correction_path']).joinpath(key + "_result.json")
            if not os.path.isfile(full_mer_path):
                full_mer_path = "//wsl.localhost/Ubuntu" + full_mer_path
                if not os.path.isfile(full_mer_path):
                    full_mer_path = os.path.join(os.path.abspath(__file__ + "/../../../"),
                                                 '/'.join(full_mer_path.split('/')[-2:]))

            with open(full_mer_path, 'r') as f:
                correction_results = json.load(f)

            mer_keys_E = [k for k, v in correction_results.items() if 'mer' in k and k.startswith('E_')]
            mer_total_2d = sum([v for k, v in correction_results.items() if k in mer_keys_E])
            for group in pp_data['groups']:
                mer_coefficients[group] = sum([v for k, v in correction_results.items()
                                               if k in mer_keys_E and group.lower() in k.lower()]) / mer_total_2d

            with open(key + '_mer_coefficients.json', 'w') as f:
                json.dump(mer_coefficients, f)

            mer_total = sum([v for k, v in energy.items() if 'mer' in k])

            epr_dict[key] = {}
            for group in pp_data['groups']:
                epr = {k: v / total_energy for k, v in energy.items() if group in k}
                epr_dict[key]["p_" + group + '_nonmer'] = sum([v for k, v in epr.items() if 'mer' not in k])
                epr_dict[key]["p_" + group + '_mer'] = sum([v for k, v in epr.items() if 'mer' in k])
                epr_dict[key]["p_" + group + '_mer_fixed'] = mer_total * mer_coefficients[group] / total_energy
                epr_dict[key]["p_" + group] = sum(epr.values())
                epr_dict[key]["p_" + group + '_fixed'] = (epr_dict[key]["p_" + group + '_mer_fixed'] +
                                                          epr_dict[key]["p_" + group + '_nonmer'])

    tabulate_into_csv(f'{os.path.basename(os.path.abspath(path))}_epr.csv', epr_dict, parameters, parameter_values)
