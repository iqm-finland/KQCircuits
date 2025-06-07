# WHAT IS THIS FILE?
# This file contains a .py "blank-slate" state that can be loaded into ParaView to set a common departing point for subsequent macros. It is used as part of simulations when there is a need to automate rendering in ParaView.

# WHY DOES THIS FILE TRIGGER "PYTHON ANALYSIS" WARNINGS WHEN OPENED IN VSCODE OR SIMILAR SOFTWARE?
# This file uses dependencies that are NOT KQCircuits dependencies because it does NOT run within the KQCircuits environment.
# The file is copied over to an output folder and ultimately runs from within a ParaView window.
# ParaView has an in-built Python environment with its own packages.
#
# If you use VSCode, you can disable python analysis warnings by adding the following to your `.vscode/settings.json`:
#   ```
#   {
#       ...
#           "python.analysis.ignore": [ "**/paraview_macro.py", "**/paraview_state.py"]
#       ...
#   }
#   ```


# FOUNDATIONAL STATE FILE GENERATED USING PARAVIEW V. 6.0.0-RC1
import paraview

paraview.compatibility.major = 6
paraview.compatibility.minor = 0

# IMPORTS
from paraview.simple import *

paraview.simple._DisableFirstRenderCameraReset()

# SETUP VIEWS
# Get material library
materialLibrary1 = GetMaterialLibrary()

# Create a foundational render view
renderView1 = CreateView("RenderView")
renderView1.Set(
    ViewSize=[720, 650],
    CameraFocalDisk=1.0,
    OSPRayMaterialLibrary=materialLibrary1,
)

# LAYOUTS
# Empty active view
SetActiveView(None)

# Create layout
layout1 = CreateLayout(name="Layout #1")
layout1.AssignView(0, renderView1)
layout1.SetSize(720, 650)

# Restore active view
SetActiveView(renderView1)

# OTHER UNUSED BASIC CONFIGS
# Get time animation track, time-keeper, animation scene
timeAnimationCue1 = GetTimeTrack()
timeKeeper1 = GetTimeKeeper()
animationScene1 = GetAnimationScene()

# Init animation scene
animationScene1.Set(
    ViewModules=renderView1,
    Cues=timeAnimationCue1,
    AnimationTime=0.0,
)

# Restore active source
SetActiveSource(None)
