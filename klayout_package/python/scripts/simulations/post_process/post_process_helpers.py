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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).
import csv
import json
import skrf


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
    nominal = min(keys, key=len)

    # Load data from json files
    parameter_dict = {}
    for key, json_file in zip(keys, json_files):
        with open(json_file, "r") as f:
            definition = json.load(f)
        parameter_dict[key] = definition["parameters"]

    # Find parameters that are varied
    parameters = []
    for parameter in parameter_dict[nominal]:
        if not all(parameter_dict[key][parameter] == parameter_dict[nominal][parameter] for key in keys):
            parameters.append(parameter)

    # Return compressed parameter_dict including only varied parameters
    parameter_values = {k: [v[p] for p in parameters] for k, v in parameter_dict.items()}
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


def read_snp_network(snp_file):
    """Read sNp file and returns network and list of z0 for each port"""
    snp_network = skrf.Network(snp_file)

    # skrf.Network fails to read multiple Z0 terms from s2p file, so we do it separately.
    with open(snp_file) as file:
        lines = file.readlines()
        for line in lines:
            if line.startswith("# GHz S MA R "):
                z0s = [float(z) for z in line[13:].split()]
                if len(z0s) > 1:
                    return snp_network, z0s
    return snp_network, snp_network.z0[0]
