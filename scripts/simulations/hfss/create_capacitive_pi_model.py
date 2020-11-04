# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy's prior
# written permission.

# This is a Python 2.7 script that should be run in HFSS in order to import and run the simulation
import time
import ScriptEnv

## SET UP ENVIRONMENT
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.AddMessage("", "", 0, "Creating PI model for all ports (%s)" % time.asctime(time.localtime()))

oDesktop.RestoreWindow()
oProject = oDesktop.GetActiveProject()
oDesign = oProject.GetActiveDesign()
oBoundarySetup = oDesign.GetModule("BoundarySetup")
oOutputVariable = oDesign.GetModule("OutputVariable")
oReportSetup = oDesign.GetModule("ReportSetup")

ports = oBoundarySetup.GetExcitations()[::2]
pielements = []  # Which matrix elements we calculate
uniquepielements = []  # The unique elements (half matrix), used for plotting
for (i, port_i) in enumerate(ports):
    for (j, port_j) in enumerate(ports):
        pielements.append([port_i, port_j])
        if j >= i:
            uniquepielements.append([port_i, port_j])

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
            "Setup1 : Sweep",
            "Terminal Solution Data",
            [])

        # Estimate capacitance vs frequency assuming capacitive elements
        oOutputVariable.CreateOutputVariable(
            "C_%s_%s" % (port_i, port_j),
            "im(yy_%s_%s)/(2*pi*Freq)" % (port_i, port_j),
            "Setup1 : Sweep",
            "Terminal Solution Data",
            [])

## Reports
oReportSetup.CreateReport(
    "Capacitance vs Frequency",
    "Terminal Solution Data",
    "Rectangular Plot",
    "Setup1 : Sweep",
    ["Domain:=", "Sweep"],
    ["Freq:=", ["All"]],
    ["X Component:=", "Freq",
     "Y Component:=", ["C_%s_%s*1e15" % (p[0], p[1]) for p in uniquepielements]
     ],
    [])
oReportSetup.ChangeProperty(
    ["NAME:AllTabs",
     ["NAME:Legend",
      ["NAME:PropServers", "Capacitance vs Frequency:Legend"],
      ["NAME:ChangedProps",
       ["NAME:Show Variation Key", "Value:=", False],
       ["NAME:Show Solution Name", "Value:=", False],
       ["NAME:DockMode", "Value:=", "Dock Right"]
       ]
      ],
     ["NAME:Axis",
      ["NAME:PropServers", "Capacitance vs Frequency:AxisY1"],
      ["NAME:ChangedProps",
       ["NAME:Specify Name", "Value:=", True],
       ["NAME:Name", "Value:=", "C (fF)"]
       ]
      ]
     ])

oDesktop.AddMessage("", "", 0,
                    "PI model created (%s)" % time.asctime(time.localtime()))
