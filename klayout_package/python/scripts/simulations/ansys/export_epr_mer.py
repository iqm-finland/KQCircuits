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


# This is a Python 2.7 script that should be run in HFSS in order to export energy participation ratios
import os
import json
import csv

# Find data files
path = os.path.curdir

prefix = os.path.basename(os.path.abspath(path))

result_files = [f for f in os.listdir(path) if f.endswith('_project_energy.csv')]
definition_files = [f.replace('_project_energy.csv', '.json') for f in result_files]
keys = [f.replace('_project_energy.csv', '') for f in result_files]
nominal = min(keys, key=len)

# Load result data
data = {}
parameter_dict = {}
epr_dict = {}

epr_keys = ['MA', 'MS', 'SA', 'substrate', 'vacuum']
for key, definition_file, result_file in zip(keys, definition_files, result_files):
    with open(definition_file, 'r') as f:
        definition = json.load(f)
    with open(result_file, 'r') as f:
        reader = csv.reader(f, delimiter=',')
        result_keys = next(reader)
        result_values = next(reader)
        result = {k: float(v) for k, v in zip(result_keys, result_values)}

    parameter_dict[key] = definition['parameters']

    total_energy = result.get("total_energy []", 1.0)

    mer_correction_path = definition.get('mer_correction_path', None)
    mer_coefficients = definition.get('mer_coefficients', None)
    if mer_correction_path is not None or mer_coefficients is not None:
        if mer_correction_path is not None:
            mer_coefficients = dict()
            simulation_name = parameter_dict[key].get('name', None)
            # TODO: add some nice error message through HFSS API telling that the file
            # does not exist and it could mean that the elmer computation has not been performed
            full_mer_path = mer_correction_path+"/"+simulation_name+"_result.json"

            if not os.path.isfile(full_mer_path):
                full_mer_path = "//wsl.localhost/Ubuntu"+full_mer_path
            if not os.path.isfile(full_mer_path):
                full_mer_path = os.path.join(os.path.abspath(__file__ + "/../../../"),
                        '/'.join(full_mer_path.split('/')[-2:]))

            with open(full_mer_path, 'r') as f:
                correction_results = json.load(f)

            mer_keys_E = [k for k, v in correction_results.items() if 'mer' in k and k.startswith('E_')]
            mer_total_2d = sum([v for k, v in correction_results.items() if k in mer_keys_E])
            for epr_key in epr_keys:
                mer_coefficients[epr_key.lower()] = \
                    sum([v for k, v in correction_results.items() \
                    if k in mer_keys_E and epr_key.lower() in k])/mer_total_2d

            with open(simulation_name+'_mer_coefficients.json', 'w') as f:
                json.dump(mer_coefficients, f)

        epr_dict[key]={}
        mer_total = result.get("total_mer_energy []", 0.0)

        all_energy_keys = [k for k, v in result.items() if k.startswith("E_") and k.endswith(" []")]
        for epr_key in epr_keys:
            epr_dict[key]['E_'+epr_key+'_nonmer'] = \
                sum([v for k, v in result.items() if k in all_energy_keys and epr_key in k and 'mer' not in k])
            epr_dict[key]['E_'+epr_key+'_mer'] = \
                sum([v for k, v in result.items() if k in all_energy_keys and epr_key in k and 'mer' in k])
            epr_dict[key]['E_'+epr_key+'_mer_fixed'] = mer_total * mer_coefficients[epr_key.lower()]
            epr_dict[key]['E_'+epr_key] = \
                    epr_dict[key]['E_'+epr_key+'_mer'] + epr_dict[key]['E_'+epr_key+'_nonmer']
            epr_dict[key]['E_'+epr_key+'_fixed'] = \
                    epr_dict[key]['E_'+epr_key+'_mer_fixed'] + epr_dict[key]['E_'+epr_key+'_nonmer']
            epr_dict[key]['p_'+epr_key] = epr_dict[key]['E_'+epr_key]/total_energy
            epr_dict[key]['p_'+epr_key+'_fixed'] = epr_dict[key]['E_'+epr_key+'_fixed']/total_energy
    else:
        epr_dict[key] = {k[2:-3]: v / total_energy for
                         k, v in result.items() if k.startswith("E_") and k.endswith(" []")}

# Find parameters that are swept
parameters = []
for parameter in parameter_dict[nominal]:
    if not all(parameter_dict[key][parameter] == parameter_dict[nominal][parameter] for key in keys):
        parameters.append(parameter)

# Tabulate C matrix as CSV
with open('%s_epr.csv' % prefix, 'wb') as csvfile:  # wb for python 2?
    writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    layer_names = sorted({n for k, v in epr_dict.items() for n in v})
    writer.writerow(['key'] + parameters + layer_names)

    for key in keys:
        parameter_values = [parameter_dict[key][parameter] for parameter in parameters]
        parameter_values_str = [str(parameter_value) for parameter_value in parameter_values]
        layer_values = [str(epr_dict[key].get(n, 0.0)) for n in layer_names]
        writer.writerow([key] + parameter_values_str + layer_values)
