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
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'util'))
from util import find_varied_parameters  # pylint: disable=wrong-import-position, no-name-in-module

# Find data files
path = os.path.curdir
result_files = [f for f in os.listdir(path) if f.endswith('_project_results.json')]
if result_files:
    # Find parameters that are swept
    definition_files = [f.replace('_project_results.json', '.json') for f in result_files]
    parameters, parameter_values = find_varied_parameters(definition_files)

    # Load result data
    CMatrix_dict = {}
    for key, result_file in zip(parameter_values.keys(), result_files):
        with open(result_file, 'r') as f:
            result = json.load(f)
        CMatrix_dict[key] = result['CMatrix']

    # Tabulate C matrix as CSV
    prefix = os.path.basename(os.path.abspath(path))
    with open('%s_results.csv' % prefix, 'wb') as csvfile:  # wb for python 2?
        writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        nominal = min(parameter_values.keys(), key=len)
        port_range = range(1, len(CMatrix_dict[nominal]) + 1)
        C_names = ['C%d%d' % (i, j) for i in port_range for j in port_range]
        writer.writerow(['key'] + parameters + C_names)

        for key, values in parameter_values.items():
            parameter_values_str = [str(parameter_value) for parameter_value in values]
            C_values = [item for sublist in CMatrix_dict[key] for item in sublist]
            writer.writerow([key] + parameter_values_str + C_values)
