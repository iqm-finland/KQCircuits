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
import csv
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'util'))
from util import find_varied_parameters  # pylint: disable=wrong-import-position, no-name-in-module

# Find data files
path = os.path.curdir
result_files = [f for f in os.listdir(path) if f.endswith('_project_energy.csv')]
if result_files:
    # Find parameters that are swept
    definition_files = [f.replace('_project_energy.csv', '.json') for f in result_files]
    parameters, parameter_values = find_varied_parameters(definition_files)

    # Load result data
    epr_dict = {}
    for key, result_file in zip(parameter_values.keys(), result_files):
        with open(result_file, 'r') as f:
            reader = csv.reader(f, delimiter=',')
            result_keys = next(reader)
            result_values = next(reader)
            result = {k: float(v) for k, v in zip(result_keys, result_values)}

        total_energy = result.get("total_energy []", 1.0)
        epr_dict[key] = {k[2:-3]: v / total_energy for k, v in result.items()
                         if k.startswith("E_") and k.endswith(" []")}

    # Tabulate EPRs into CSV
    prefix = os.path.basename(os.path.abspath(path))
    with open('%s_epr.csv' % prefix, 'wb') as csvfile:  # wb for python 2?
        writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        layer_names = sorted({n for k, v in epr_dict.items() for n in v})
        writer.writerow(['key'] + parameters + layer_names)

        for key, values in parameter_values.items():
            parameter_values_str = [str(parameter_value) for parameter_value in values]
            layer_values = [str(epr_dict[key].get(n, 0.0)) for n in layer_names]
            writer.writerow([key] + parameter_values_str + layer_values)
