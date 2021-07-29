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
import os
import json
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


#######################
# Optional processing #
#######################

# Read export_processing settings from .json
with open(jsonfile, 'r') as fp:
    export_processing = json.load(fp)['export_processing']

# Time Domain Reflectometry
if 'tdr' in export_processing:
    oDesktop.RunScript(os.path.join(scriptpath, 'export_tdr.py'))

# Export Touchstone S-matrix (.sNp) w/o de-embedding
if 'snp_no_deembed' in export_processing:
    oDesktop.RunScript(os.path.join(scriptpath, 'export_snp_no_deembed.py'))
