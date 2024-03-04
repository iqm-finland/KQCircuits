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


# This is a Python 2.7 script that should be run in Ansys Electronics Desktop
# in order to create Time Domain Reflectometry and export it.
import os
import sys
import time

import ScriptEnv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "util"))
from util import get_enabled_setup, get_enabled_sweep  # pylint: disable=wrong-import-position,no-name-in-module


def create_z_vs_time_plot(report_setup, report_type, solution_name, context_array, y_label, y_components):
    report_setup.CreateReport(
        "Time Domain Reflectometry",
        report_type,
        "Rectangular Plot",
        solution_name,
        context_array,
        ["Time:=", ["All"]],
        ["X Component:=", "Time", "Y Component:=", y_components],
        [],
    )
    report_setup.ChangeProperty(
        [
            "NAME:AllTabs",
            [
                "NAME:Legend",
                ["NAME:PropServers", "Time Domain Reflectometry:Legend"],
                [
                    "NAME:ChangedProps",
                    ["NAME:Show Variation Key", "Value:=", False],
                    ["NAME:Show Solution Name", "Value:=", False],
                    ["NAME:DockMode", "Value:=", "Dock Right"],
                ],
            ],
            [
                "NAME:Axis",
                ["NAME:PropServers", "Time Domain Reflectometry:AxisY1"],
                ["NAME:ChangedProps", ["NAME:Specify Name", "Value:=", True], ["NAME:Name", "Value:=", y_label]],
            ],
        ]
    )
    report_setup.ExportToFile("Time Domain Reflectometry", csv_filename)


# Set up environment
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.AddMessage("", "", 0, "Plotting TDR for all ports (%s)" % time.asctime(time.localtime()))

oDesktop.RestoreWindow()
oProject = oDesktop.GetActiveProject()
oDesign = oProject.GetActiveDesign()
oBoundarySetup = oDesign.GetModule("BoundarySetup")
oReportSetup = oDesign.GetModule("ReportSetup")

# Set file name
path = oProject.GetPath()
basename = oProject.GetName()
csv_filename = os.path.join(path, basename + "_TDR.csv")

# No de-embedding
oDesign.ChangeProperty(
    [
        "NAME:AllTabs",
        [
            "NAME:HfssTab",
            ["NAME:PropServers", "BoundarySetup:1"],
            ["NAME:ChangedProps", ["NAME:Renorm All Terminals", "Value:=", False, "NAME:Deembed", "Value:=", False]],
        ],
    ]
)
oDesign.ChangeProperty(
    [
        "NAME:AllTabs",
        [
            "NAME:HfssTab",
            ["NAME:PropServers", "BoundarySetup:2"],
            ["NAME:ChangedProps", ["NAME:Renorm All Terminals", "Value:=", False, "NAME:Deembed", "Value:=", False]],
        ],
    ]
)

# Create model only for HFSS
design_type = oDesign.GetDesignType()
if design_type == "HFSS":
    setup = get_enabled_setup(oDesign)
    if oDesign.GetSolutionType() == "HFSS Terminal Network":
        sweep = get_enabled_sweep(oDesign, setup)
        solution = setup + (" : LastAdaptive" if sweep is None else " : " + sweep)
        context = (
            []
            if sweep is None
            else [
                "Domain:=",
                "Time",
                "HoldTime:=",
                1,
                "RiseTime:=",
                10e-12,  # picoseconds
                "StepTime:=",
                2e-12,
                "Step:=",
                True,
                "WindowWidth:=",
                1,
                "WindowType:=",
                4,  # Hanning
                "KaiserParameter:=",
                4.44659081257122e-323,
                "MaximumTime:=",
                200e-12,
            ]
        )

        ports = oBoundarySetup.GetExcitations()[::2]

        create_z_vs_time_plot(
            oReportSetup,
            "Terminal Solution Data",
            solution,
            context,
            "Z [Ohm]",
            ["TDRZt(%s)" % (port) for port in ports],
        )

# Notify the end of script
oDesktop.AddMessage("", "", 0, "TDR created (%s)" % time.asctime(time.localtime()))
