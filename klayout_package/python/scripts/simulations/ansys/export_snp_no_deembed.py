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
# in order to export non de-embedded S-matrix network data.
import os
import ScriptEnv

ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.RestoreWindow()
oProject = oDesktop.GetActiveProject()
oDesign = oProject.GetActiveDesign()

path = oProject.GetPath()
basename = oProject.GetName()

oDesign.ChangeProperty(
    [
        "NAME:AllTabs",
        [
            "NAME:HfssTab",
            ["NAME:PropServers", "BoundarySetup:1"],
            [
                "NAME:ChangedProps",
                [
                    "NAME:Deembed Dist",
                    "Value:=",
                    "0um",
                    "NAME:Renorm All Terminals",
                    "Value:=",
                    False,
                    "NAME:Deembed",
                    "Value:=",
                    False,
                ],
            ],
        ],
    ]
)
oDesign.ChangeProperty(
    [
        "NAME:AllTabs",
        [
            "NAME:HfssTab",
            ["NAME:PropServers", "BoundarySetup:2"],
            [
                "NAME:ChangedProps",
                [
                    "NAME:Deembed Dist",
                    "Value:=",
                    "0um",
                    "NAME:Renorm All Terminals",
                    "Value:=",
                    False,
                    "NAME:Deembed",
                    "Value:=",
                    False,
                ],
            ],
        ],
    ]
)

oModule = oDesign.GetModule("Solutions")
oModule.ExportNetworkData(
    "",
    ["Setup1:Sweep"],
    3,
    os.path.join(path, basename + "_SMatrix_nodeembed.s2p"),
    ["All"],
    False,
    50,
    "S",
    -1,
    0,
    15,
    True,
    True,
    True,
)

oProject.Save()
