# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy's prior
# written permission.

# This is a Python 2.7 script that should be run in HFSS in order to import and run the simulation
import os
import ScriptEnv

# Set up environment
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
scriptpath = os.path.dirname(__file__)

jsonfile = ScriptArgument
path = os.path.dirname(jsonfile)
basename = os.path.splitext(os.path.basename(jsonfile))[0]

# Create project and geometry
oDesktop.RunScriptWithArguments(os.path.join(scriptpath, 'import_simulation_geometry.py'), jsonfile)

# Set up capacitive PI model results
oDesktop.RunScript(os.path.join(scriptpath, 'create_capacitive_pi_model.py'))
oDesktop.TileWindows(0)

# Save project
oProject = oDesktop.GetActiveProject()
oProject.SaveAs(os.path.join(path, basename + '_project.aedt'), True)

# Run
oDesign = oProject.GetActiveDesign()
oDesign.AnalyzeAll()

# Save solution
oProject.Save()

# Export results
oDesktop.RunScript(os.path.join(scriptpath, 'export_solution_data.py'))
