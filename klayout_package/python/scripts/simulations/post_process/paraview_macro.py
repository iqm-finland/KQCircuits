# WHAT IS THIS FILE?
# This file contains a .py "macro" that runs from within ParaView to automatically load and format of data files created during simulations.

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


# IMPORTS
from paraview.simple import *

paraview.simple._DisableFirstRenderCameraReset()

# RE-WRITABLE VARIABLES
# Since you cannot pass variables to a ParaView macro,
# the variables below are written/re-written externally before running the Macro inside ParaView.
data_folder = ""
data_files = []
kwargs = {"enable": True, "threshold": [1, 1], "threshold_scalars": ["CELLS", "GeometryIds"]}

# LOAD DATA FILES
registration_names = [f.rsplit("/")[1].split(".")[0] for f in data_files]
for i in range(len(registration_names)):
    reader = XMLPartitionedUnstructuredGridReader(
        FileName=[data_folder + "/" + data_files[i]], registrationName=registration_names[i]
    )
    reader.TimeArray = "None"

# INIT VIEW
render_view = GetActiveViewOrCreate("RenderView")

# FORMAT DATA
for i in range(len(registration_names)):
    parent = FindSource(registration_names[i])
    parent.TimeArray = "None"
    display = Show(parent, render_view, "UnstructuredGridRepresentation")
    display.Representation = "Surface"
    display.SetScalarBarVisibility(render_view, True)
    Hide(parent, render_view)

# ADD THRESHOLDS
for i in range(len(registration_names)):
    parent = FindSource(registration_names[i])
    threshold = Threshold(registrationName=f"{registration_names[i]}-threshold", Input=parent)
    threshold.ThresholdMethod = "Between"
    threshold.LowerThreshold = kwargs["threshold"][0]
    threshold.UpperThreshold = kwargs["threshold"][1]
    threshold.Scalars = kwargs["threshold_scalars"]
    threshold_display = Show(threshold, render_view, "UnstructuredGridRepresentation")
    threshold_display.Representation = "Surface"
    threshold_display.SetScalarBarVisibility(render_view, True)
    if i + 1 < len(registration_names):
        Hide(threshold, render_view)

# UPDATE COLOURS
potentialLUT = GetColorTransferFunction("potential")
potentialPWF = GetOpacityTransferFunction("potential")
potentialTF2D = GetTransferFunction2D("potential")

# UPDATE LAYOUT & VIEW
layout = GetLayout()
layout.SetSize(720, 650)
render_view.ResetCamera(False, 0.9)
render_view.Update()
render_view.Set(
    CameraPosition=[0.001, 0.001, 0.006455783139039206],
    CameraFocalPoint=[0.001, 0.001, 0.00022500000000000005],
    CameraParallelScale=0.0016126453422870138,
)
