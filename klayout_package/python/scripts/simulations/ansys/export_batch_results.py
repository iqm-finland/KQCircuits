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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).


# This is a Python 2.7 script that should be run in HFSS in order to import and run the simulation
import os
import json
import csv

# Find data files
path = os.path.curdir

prefix = os.path.basename(os.path.abspath(path))

result_files = [f for f in os.listdir(path) if f.endswith('_project_results.json')]
definition_files = [f.replace('_project_results.json', '.json') for f in result_files]
keys = [f.replace('_project_results.json', '') for f in result_files]
nominal = min(keys, key=len)

# Load result data
data = {}
parameter_dict = {}
CMatrix_dict = {}

for key, definition_file, result_file in zip(keys, definition_files, result_files):
    with open(definition_file, 'r') as f:
        definition = json.load(f)
    with open(result_file, 'r') as f:
        result = json.load(f)
    data[key] = {'definition': definition, 'result': result}

    parameter_dict[key] = definition['parameters']
    CMatrix_dict[key] = result['CMatrix']

# Find parameters that are swept
parameters = []
for parameter in parameter_dict[nominal]:
    if not all(parameter_dict[key][parameter] == parameter_dict[nominal][parameter] for key in keys):
        parameters.append(parameter)

# Tabulate C matrix as CSV
with open('%s_results.csv' % prefix, 'wb') as csvfile:  # wb for python 2?
    writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    port_range = range(1, len(CMatrix_dict[nominal]) + 1)
    C_names = ['C%d%d' % (i, j) for i in port_range for j in port_range]
    writer.writerow(['key'] + parameters + C_names)

    for key in keys:
        parameter_values = [parameter_dict[key][parameter] for parameter in parameters]
        parameter_values_str = [str(parameter_value) for parameter_value in parameter_values]
        C_values = [item for sublist in CMatrix_dict[key] for item in sublist]
        writer.writerow([key] + parameter_values_str + C_values)
