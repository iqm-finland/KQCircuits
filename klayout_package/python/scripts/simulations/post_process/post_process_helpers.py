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
import csv
import json


def find_varied_parameters(json_files):
    """Finds the parameters that vary between the definitions in the json files.

    Args:
        json_files: List of json file names

    Returns:
        tuple (list, dict)
        - list of parameter names
        - dictionary with json file prefix as key and list of parameter values as value
    """
    keys = [f.replace(".json", "") for f in json_files]

    # Load data from json files
    nominal_parameters = {}
    parameter_dict = {}
    for key, json_file in zip(keys, json_files):
        with open(json_file, "r") as f:
            definition = json.load(f)
        parameter_dict[key] = definition["parameters"]
        nominal_parameters.update(parameter_dict[key])

    # Find parameters that are varied
    parameters = []
    for k, v in nominal_parameters.items():
        if any(k in parameter_dict[key] and parameter_dict[key][k] != v for key in keys):
            parameters.append(k)

    # Return compressed parameter_dict including only varied parameters
    parameter_values = {k: [v[p] if p in v else None for p in parameters] for k, v in parameter_dict.items()}
    return parameters, parameter_values


def tabulate_into_csv(file_name, data_dict, parameters, parameter_values):
    """Tabulate dictionary data into CSV

    Args:
        file_name: output csv file name
        data_dict: dictionary with relevant data to be saved
        parameters: list of parameter names changed between simulations
        parameter_values: dictionary with list of parameter values as value
    """
    with open(file_name, "w") as csvfile:
        writer = csv.writer(csvfile, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)

        layer_names = sorted({n for v in data_dict.values() for n in v})
        writer.writerow(["key"] + parameters + layer_names)

        for key, values in parameter_values.items():
            parameter_values_str = [str(parameter_value) for parameter_value in values]
            layer_values = [str(data_dict[key].get(n, 0.0)) for n in layer_names]
            writer.writerow([key] + parameter_values_str + layer_values)
