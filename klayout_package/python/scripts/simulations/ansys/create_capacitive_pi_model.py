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


import os
import sys
# This is a Python 2.7 script that should be run in Ansys Electronics Desktop in order to create plot of capacitance
# matrix elements.
import time

import ScriptEnv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'util'))
from util import get_enabled_setup_and_sweep, get_enabled_setup, create_x_vs_y_plot \
                 # pylint: disable=wrong-import-position,no-name-in-module


# Set up environment
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")

oDesktop.RestoreWindow()
oProject = oDesktop.GetActiveProject()
oDesign = oProject.GetActiveDesign()
oBoundarySetup = oDesign.GetModule("BoundarySetup")
oOutputVariable = oDesign.GetModule("OutputVariable")
oReportSetup = oDesign.GetModule("ReportSetup")


# Create model separately for HFSS and Q3D
design_type = oDesign.GetDesignType()
if design_type in {"HFSS", "Q3D Extractor"}:
    oDesktop.AddMessage("", "", 0, "Creating PI model for all ports (%s)" % time.asctime(time.localtime()))

    if design_type == "HFSS" and oDesign.GetSolutionType() == "HFSS Terminal Network":
        (setup, sweep) = get_enabled_setup_and_sweep(oDesign)
        solution = setup + (" : LastAdaptive" if sweep is None else " : " + sweep)
        context = [] if sweep is None else ["Domain:=", "Sweep"]

        ports = oBoundarySetup.GetExcitations()[::2]
        unique_elements_c = []  # The unique elements (half matrix), used for plotting C-matrix
        unique_elements_s = []  # The unique elements (half matrix), used for plotting S-matrix
        for (i, port_i) in enumerate(ports):
            for (j, port_j) in enumerate(ports):
                # PI model admittance element
                if i == j:
                    # admittance yii between port i and ground
                    expression = " + ".join(
                        ["Yt(%s,%s)" % (port_i, port_k) for port_k in ports])
                else:
                    # admittance yij between port i and j
                    expression = "-Yt(%s,%s)" % (port_i, port_j)

                oOutputVariable.CreateOutputVariable(
                    "yy_%s_%s" % (port_i, port_j),
                    expression,
                    solution,
                    "Terminal Solution Data",
                    [])

                # Estimate capacitance vs frequency assuming capacitive elements
                oOutputVariable.CreateOutputVariable(
                    "C_%s_%s" % (port_i, port_j),
                    "im(yy_%s_%s)/(2*pi*Freq)" % (port_i, port_j),
                    solution,
                    "Terminal Solution Data",
                    [])

                if j >= i:
                    unique_elements_c.append("C_%s_%s" % (port_i, port_j))
                    unique_elements_s.append("dB(St(%s,%s))" % (port_i, port_j))

        create_x_vs_y_plot(oReportSetup, "Capacitance vs Frequency", "Terminal Solution Data", solution, context,
                        ["Freq:=", ["All"]], "Freq", "C [fF]", unique_elements_c)
        create_x_vs_y_plot(oReportSetup, "S vs Frequency", "Terminal Solution Data", setup + " : LastAdaptive", context,
                        ["Freq:=", ["All"]], "Freq", "S [dB]", unique_elements_s)
        create_x_vs_y_plot(oReportSetup, "Solution Convergence", "Terminal Solution Data", setup + " : AdaptivePass",
                        context, ["Pass:=", ["All"], "Freq:=", ["All"]], "Pass", "S [dB]", unique_elements_s)

    elif design_type == "Q3D Extractor":
        nets = oBoundarySetup.GetExcitations()[::2]
        net_types = oBoundarySetup.GetExcitations()[1::2]
        signal_nets = [net for net, net_type in zip(nets, net_types) if net_type == 'SignalNet']

        unique_elements = [] # The unique elements (half matrix), used for plotting
        for (i, net_i) in enumerate(signal_nets):
            for (j, net_j) in enumerate(signal_nets):
                if i == j:
                    expression = " + ".join(["C({},{})".format(net_i, net_k) for net_k in signal_nets])
                else:
                    expression = "-C({},{})".format(net_i, net_j)

                oOutputVariable.CreateOutputVariable(
                    "C_{}_{}".format(net_i, net_j),
                    expression,
                    get_enabled_setup(oDesign) + " : LastAdaptive",
                    "Matrix",
                    ["Context:=", "Original"])

                if j >= i:
                    unique_elements.append("C_{}_{}".format(net_i, net_j))

        create_x_vs_y_plot(oReportSetup, "Capacitance vs Frequency", "Matrix",
                        get_enabled_setup(oDesign) + " : LastAdaptive", ["Context:=", "Original"],
                        ["Freq:=", ["All"]], "Freq", "C", unique_elements)
        create_x_vs_y_plot(oReportSetup, "Solution Convergence", "Matrix",
                        get_enabled_setup(oDesign) + " : AdaptivePass",
                        ["Context:=", "Original"], ["Pass:=", ["All"], "Freq:=", ["All"]], "Pass", "C",
                        unique_elements)

    # Notify the end of script
    oDesktop.AddMessage("", "", 0, "PI model created (%s)" % time.asctime(time.localtime()))
