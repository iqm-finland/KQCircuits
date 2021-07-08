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
import time
import os
import sys
import json
import ScriptEnv

# TODO: Figure out how to set the python path for the HFSS internal IronPython
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'util'))
from util import get_enabled_setup, get_enabled_setup_and_sweep, get_solution_data, \
    ComplexEncoder  # pylint: disable=wrong-import-position


def calculate_total_capacitance_to_ground(c_matrix):
    """Returns total capacitance to ground for each column of c_matrix."""
    columns = range(len(c_matrix))
    c_ground = []
    for i in columns:
        c_ground.append(
            c_matrix[i][i] + sum([c_matrix[i][j] / (1.0 + c_matrix[i][j] / c_matrix[j][j]) for j in columns if i != j]))
    return c_ground


def save_capacitance_matrix(file_name, c_matrix, c_to_ground, detail=''):
    """Save capacitance matrix in readable format. """
    with open(file_name, 'w') as out_file:
        out_file.write("Capacitance matrix" + detail + ":\n" + '\n'.join(
            ['\t'.join(['%8.3f' % (item * 1e15) for item in row]) for row in c_matrix]) + '\n')
        out_file.write("Total capacitance to ground" + detail + ":\n" +
                       '\t'.join(['%8.3f' % (item * 1e15) for item in c_to_ground]) + '\n')


# Set up environment
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.AddMessage("", "", 0, "Exporting PI model results (%s)" % time.asctime(time.localtime()))

oDesktop.RestoreWindow()
oProject = oDesktop.GetActiveProject()
oDesign = oProject.GetActiveDesign()
oBoundarySetup = oDesign.GetModule("BoundarySetup")
oOutputVariable = oDesign.GetModule("OutputVariable")
oReportSetup = oDesign.GetModule("ReportSetup")

# Set file names
path = oProject.GetPath()
basename = oProject.GetName()
matrix_filename = os.path.join(path, basename + '_CMatrix.txt')
json_filename = os.path.join(path, basename + '_results.json')

# Export solution data separately for HFSS and Q3D
design_type = oDesign.GetDesignType()
if design_type == "HFSS":
    freq = '1GHz'  # export frequency
    (setup, sweep) = get_enabled_setup_and_sweep(oDesign)
    solution = setup + (" : LastAdaptive" if sweep is None else " : " + sweep)
    context = [] if sweep is None else ["Domain:=", "Sweep"]
    families = ["Freq:=", [freq]]

    # Get list of ports
    ports = oBoundarySetup.GetExcitations()[::2]

    # Get solution data
    yyMatrix = [[get_solution_data(oReportSetup, "Terminal Solution Data", solution, context, families,
                                   "yy_{}_{}".format(port_i, port_j))[0] for port_j in ports] for port_i in ports]
    CMatrix = [[get_solution_data(oReportSetup, "Terminal Solution Data", solution, context, families,
                                  "C_{}_{}".format(port_i, port_j))[0] for port_j in ports] for port_i in ports]
    Cg = calculate_total_capacitance_to_ground(CMatrix)

    # Save capacitance matrix into readable format
    save_capacitance_matrix(matrix_filename, CMatrix, Cg, detail=' at ' + freq)

    # Save results in json format
    with open(json_filename, 'w') as outfile:
        json.dump({'CMatrix': CMatrix,
                   'Cg': Cg,
                   'yyMatrix': yyMatrix,
                   'freq': freq,
                   'yydata': get_solution_data(oReportSetup, "Terminal Solution Data", solution, context, families,
                                               ["yy_{}_{}".format(port_i, port_j) for port_j in ports
                                                for port_i in ports]),
                   'Cdata': get_solution_data(oReportSetup, "Terminal Solution Data", solution, context, families,
                                              ["C_{}_{}".format(port_i, port_j) for port_j in ports
                                               for port_i in ports])
                   }, outfile, cls=ComplexEncoder, indent=4)

    # S-parameter export (only for HFSS)
    file_format = 3  # 2 = Tab delimited (.tab), 3 = Touchstone (.sNp), 4 = CitiFile (.cit), 7 = Matlab  (.m), ...
    file_name = os.path.join(path, basename + '_SMatrix.s2p')
    frequencies = ["All"]
    do_renormalize = False
    renorm_impedance = 50
    data_type = "S"
    pass_number = -1  # -1 = all passes
    complex_format = 0  # 0 = magnitude/phase, 1 = real/imag, 2 = dB/phase
    precision = 8
    show_gamma_and_impedance = False

    oSolutions = oDesign.GetModule("Solutions")
    oSolutions.ExportNetworkData("", solution, file_format, file_name, frequencies, do_renormalize, renorm_impedance,
                                 data_type, pass_number, complex_format, precision, True, show_gamma_and_impedance,
                                 True)

elif design_type == "Q3D Extractor":
    solution = get_enabled_setup(oDesign) + " : LastAdaptive"
    context = ["Context:=", "Original"]

    # Get list of signal nets
    nets = oBoundarySetup.GetExcitations()[::2]
    net_types = oBoundarySetup.GetExcitations()[1::2]
    signal_nets = [net for net, net_type in zip(nets, net_types) if net_type == 'SignalNet']

    # Get solution data
    CMatrix = [[get_solution_data(oReportSetup, "Matrix", solution, context, [],
                                  "C_{}_{}".format(net_i, net_j))[0] for net_j in signal_nets] for net_i in signal_nets]
    Cg = calculate_total_capacitance_to_ground(CMatrix)

    # Save capacitance matrix into readable format
    save_capacitance_matrix(matrix_filename, CMatrix, Cg)

    # Save results in json format
    with open(json_filename, 'w') as outfile:
        json.dump({'CMatrix': CMatrix,
                   'Cg': Cg,
                   'Cdata': get_solution_data(oReportSetup, "Matrix", solution, context, [],
                                              ["C_{}_{}".format(net_i, net_j) for net_j in signal_nets for net_i in
                                               signal_nets])
                   }, outfile, cls=ComplexEncoder, indent=4)

# Notify the end of script
oDesktop.AddMessage("", "", 0, "Done exporting PI model results (%s)" % time.asctime(time.localtime()))
