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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


# This is a Python 2.7 script that should be run in Ansys Electronics Desktop in order to create reports.
import os
import sys
import time

import ScriptEnv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "util"))
from util import (  # pylint: disable=wrong-import-position,no-name-in-module
    get_enabled_setup,
    get_enabled_sweep,
    create_x_vs_y_plot,
    get_quantities,
)

# pylint: disable=consider-using-f-string
# Set up environment
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")

oDesktop.RestoreWindow()
oProject = oDesktop.GetActiveProject()
oDesign = oProject.GetActiveDesign()
oBoundarySetup = oDesign.GetModule("BoundarySetup")
oOutputVariable = oDesign.GetModule("OutputVariable")
oReportSetup = oDesign.GetModule("ReportSetup")

# Create model separately for HFSS and Q3D
oDesktop.AddMessage("", "", 0, "Creating reports (%s)" % time.asctime(time.localtime()))

design_type = oDesign.GetDesignType()
if design_type == "HFSS":
    setup = get_enabled_setup(oDesign)
    if oDesign.GetSolutionType() == "HFSS Terminal Network":
        sweep = get_enabled_sweep(oDesign, setup)
        solution = setup + (" : LastAdaptive" if sweep is None else " : " + sweep)
        context = [] if sweep is None else ["Domain:=", "Sweep"]
        ports = oBoundarySetup.GetExcitations()[::2]

        # Create capacitance vs frequency report
        unique_elements_c = [
            "C_%s_%s" % (port_i, ports[j]) for i, port_i in enumerate(ports) for j in range(i, len(ports))
        ]  # The unique elements (half matrix), used for plotting C-matrix
        unique_output_c = [e for e in unique_elements_c if e in oOutputVariable.GetOutputVariables()]
        if unique_output_c:
            create_x_vs_y_plot(
                oReportSetup,
                "Capacitance vs Frequency",
                "Terminal Solution Data",
                solution,
                context,
                ["Freq:=", ["All"]],
                "Freq",
                "C [fF]",
                unique_output_c,
            )

        # Create S vs frequency and S convergence reports
        unique_elements_s = [
            "St(%s,%s)" % (port_i, ports[j]) for i, port_i in enumerate(ports) for j in range(i, len(ports))
        ]  # The unique elements (half matrix), used for plotting S-matrix
        unique_output_s = [
            "dB(%s)" % e
            for e in unique_elements_s
            if e in get_quantities(oReportSetup, "Terminal Solution Data", solution, context, "Terminal S Parameter")
        ]
        if unique_output_s:
            create_x_vs_y_plot(
                oReportSetup,
                "S vs Frequency",
                "Terminal Solution Data",
                solution,
                context,
                ["Freq:=", ["All"]],
                "Freq",
                "S [dB]",
                unique_output_s,
            )
            create_x_vs_y_plot(
                oReportSetup,
                "Solution Convergence",
                "Terminal Solution Data",
                setup + " : Adaptivepass",
                [],
                ["Pass:=", ["All"], "Freq:=", ["All"]],
                "Pass",
                "S [dB]",
                unique_output_s,
            )

    elif oDesign.GetSolutionType() == "Eigenmode":
        # Create eigenmode convergence report
        solution = setup + " : AdaptivePass"
        modes = get_quantities(oReportSetup, "Eigenmode Parameters", solution, [], "Eigen Modes")
        create_x_vs_y_plot(
            oReportSetup,
            "Solution Convergence",
            "Eigenmode Parameters",
            solution,
            [],
            ["Pass:=", ["All"]],
            "Pass",
            "Frequency [Hz]",
            ["re({})".format(m) for m in modes],
        )

    # Create integral reports
    solution = setup + " : LastAdaptive"
    integrals = get_quantities(oReportSetup, "Fields", solution, [], "Calculator Expressions")
    energies = [e for e in integrals if e.startswith("E_") or e.startswith("Ez_") or e.startswith("Exy_")]
    input_family = ["Phase:=", ["0deg"]] + ([] if oDesign.GetSolutionType() == "Eigenmode" else ["Freq:=", ["All"]])
    if energies:
        create_x_vs_y_plot(
            oReportSetup, "Energy Integrals", "Fields", solution, [], input_family, "Phase", "E [J]", energies
        )
    fluxes = [e for e in integrals if e.startswith("flux_")]
    if fluxes:
        create_x_vs_y_plot(
            oReportSetup,
            "Magnetic Fluxes",
            "Fields",
            solution,
            [],
            input_family,
            "Phase",
            "Magnetic flux quanta",
            fluxes,
        )

elif design_type == "Q3D Extractor":
    setup = get_enabled_setup(oDesign, tab="General")
    nets = oBoundarySetup.GetExcitations()[::2]
    net_types = oBoundarySetup.GetExcitations()[1::2]
    signal_nets = [net for net, net_type in zip(nets, net_types) if net_type == "SignalNet"]

    # Create capacitance vs frequency and capacitance convergence reports
    unique_elements_c = ["C_%s_%s" % (net_i, net_j) for i, net_i in enumerate(signal_nets) for net_j in signal_nets[i:]]
    unique_output_c = [e for e in unique_elements_c if e in oOutputVariable.GetOutputVariables()]
    if unique_output_c:
        create_x_vs_y_plot(
            oReportSetup,
            "Capacitance vs Frequency",
            "Matrix",
            setup + " : LastAdaptive",
            ["Context:=", "Original"],
            ["Freq:=", ["All"]],
            "Freq",
            "C",
            unique_output_c,
        )
        create_x_vs_y_plot(
            oReportSetup,
            "Solution Convergence",
            "Matrix",
            setup + " : AdaptivePass",
            ["Context:=", "Original"],
            ["Pass:=", ["All"], "Freq:=", ["All"]],
            "Pass",
            "C",
            unique_output_c,
        )

elif design_type == "2D Extractor":
    setup = get_enabled_setup(oDesign, tab="General")
    each_pass = setup + " : AdaptivePass"
    context = ["Context:=", "Original"]

    conductors = oBoundarySetup.GetExcitations()[::2]
    conductor_types = oBoundarySetup.GetExcitations()[1::2]
    signals = sorted([c for c, c_type in zip(conductors, conductor_types) if c_type == "SignalLine"])

    # Create capacitance report
    unique_elements_c = ["C_%s_%s" % (s_i, s_j) for i, s_i in enumerate(signals) for s_j in signals[i:]]
    unique_output_c = [e for e in unique_elements_c if e in oOutputVariable.GetOutputVariables()]
    create_x_vs_y_plot(
        oReportSetup,
        "Capacitance Convergence",
        "Matrix",
        each_pass,
        context,
        ["Pass:=", ["All"], "Freq:=", ["All"]],
        "Pass",
        "Capacitance per unit length",
        unique_output_c,
    )

    # Create inductance report
    unique_elements_l = ["L(%s,%s)" % (s_i, s_j) for i, s_i in enumerate(signals) for s_j in signals[i:]]
    output_l = get_quantities(oReportSetup, "Matrix", each_pass, context, "L Matrix")
    unique_output_l = [e for e in unique_elements_l if e in output_l]
    create_x_vs_y_plot(
        oReportSetup,
        "Inductance Convergence",
        "Matrix",
        each_pass,
        context,
        ["Pass:=", ["All"], "Freq:=", ["All"]],
        "Pass",
        "Inductance per unit length",
        unique_output_l,
    )

    # Create integral reports
    solution = setup + " : LastAdaptive"
    integrals = get_quantities(oReportSetup, "CG Fields", solution, context, "Calculator Expressions")
    energies = [e for e in integrals if e.startswith("E_")]
    if energies:
        create_x_vs_y_plot(
            oReportSetup,
            "Energy Integrals",
            "CG Fields",
            solution,
            context,
            ["Phase:=", ["0deg"]],
            "Phase",
            "E [J]",
            energies,
        )

# Notify the end of script
oDesktop.AddMessage("", "", 0, "Reports created (%s)" % time.asctime(time.localtime()))
# pylint: enable=consider-using-f-string
