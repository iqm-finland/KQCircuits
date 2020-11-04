# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy's prior
# written permission.

# This is a Python 2.7 script that should be run in HFSS in order to import and run the simulation
import os
import ScriptEnv

## SET UP ENVIRONMENT
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
scriptpath = os.path.dirname(__file__)

jsonfile = ScriptArgument
path = os.path.dirname(jsonfile)
basename = os.path.splitext(os.path.basename(jsonfile))[0]

# Create project and geometry
oDesktop.RunScriptWithArguments(os.path.join(scriptpath, 'import_simulation_geometry.py'), jsonfile)
oProject = oDesktop.GetActiveProject()
oDesign = oProject.GetActiveDesign()

# Set up capacitive PI model results
oDesktop.RunScript(os.path.join(scriptpath, 'create_capacitive_pi_model.py'))
oDesktop.TileWindows(0)

# Save project
oProject.SaveAs(os.path.join(path, basename + '_project.aedt'), True)

# Run
oDesign.Analyze("Setup1")

# Save solution
oProject.Save()

# Export results from capacitive PI model
oDesktop.RunScript(os.path.join(scriptpath, 'export_capacitive_pi_model.py'))
