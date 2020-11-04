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

oDesktop.RestoreWindow()
oProject = oDesktop.GetActiveProject()
oDesign = oProject.GetActiveDesign()
oOutputVariable = oDesign.GetModule("OutputVariable")

outputvars = oOutputVariable.GetOutputVariables()
for x in outputvars:
    oOutputVariable.DeleteOutputVariable(x)

oDesktop.AddMessage("", "", 0, "Deleted %d output variables (%s)" % (len(outputvars), time.asctime(time.localtime())))
