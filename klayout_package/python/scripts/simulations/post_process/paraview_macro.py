# WHAT IS THIS FILE?
# This file contains a .py "macro" that runs from within ParaView to automatically load and format of data files created during simulations.

# WHY DOES THIS FILE TRIGGER "PYTHON ANALYSIS" WARNINGS WHEN OPENED IN VSCODE OR SIMILAR SOFTWARE?
# This file uses dependencies that are NOT KQCircuits dependencies because it runs from within ParaView, which has its own environment.
# If you use VSCode, you can disable python analysis warnings by adding the following to your `.vscode/settings.json`:
#   ```
#   {
#       "python.analysis.ignore": [ "**/paraview_macro.py"]
#   }
#   ```

# IMPORTS
import json
from paraview.simple import *

paraview.simple._DisableFirstRenderCameraReset()

# RE-WRITABLE PARAMS
# Per sweep, as applicable, params below are re-written automatically before Macro runs in ParaView.
data_folder = ""
data_files = []
simulation_root_name = None
cross_section = False
registration_names = []
thresholds = []
vtu_pvtu = None
new_box = None

# LOAD DATA FILES
if data_files:
    simulation_root_name = "" if not data_files else data_files[0].split("/")[0]
    registration_names = [f.rsplit("/")[1].split(".")[0] for f in data_files]
    vtu_pvtu = data_files[0].rsplit(".")[1]
    if vtu_pvtu == "pvtu":
        for i in range(len(registration_names)):
            reader = XMLPartitionedUnstructuredGridReader(
                FileName=[data_folder + "/" + data_files[i]], registrationName=registration_names[i]
            )
            reader.TimeArray = "None"
    elif vtu_pvtu == "vtu":
        for i in range(len(registration_names)):
            reader = XMLUnstructuredGridReader(
                FileName=[data_folder + "/" + data_files[i]], registrationName=registration_names[i]
            )
            reader.TimeArray = "None"
    else:
        raise FileNotFoundError("Invalid or no simulation files given to ParaView.")

# INIT VIEW
render_view = GetActiveViewOrCreate("RenderView")

# FORMATTING
# Data
if data_files:
    for i in range(len(registration_names)):
        parent = FindSource(registration_names[i])

        if vtu_pvtu == "pvtu":
            parent.TimeArray = "None"

        display = Show(parent, render_view, "UnstructuredGridRepresentation")
        display.Representation = "Surface With Edges"
        display.EdgeColor = (1.0, 1.0, 0.0)

        if vtu_pvtu == "pvtu":
            display.Opacity = 0.2
            display.SetScalarBarVisibility(render_view, True)
        else:
            ColorBy(display, ("POINTS", "potential"))

        if i + 1 < len(registration_names):
            Hide(parent, render_view)


# Other (as applicable)
if vtu_pvtu:
    # Thresholds
    if vtu_pvtu == "pvtu" and thresholds:
        for i in range(len(registration_names)):
            parent = FindSource(registration_names[i])
            threshold = Threshold(registrationName=f"{registration_names[i]}-threshold", Input=parent)
            threshold.ThresholdMethod = "Between"
            threshold.LowerThreshold = thresholds[0]
            threshold.UpperThreshold = thresholds[1]
            threshold.Scalars = ["CELLS", "GeometryIds"]
            threshold_display = Show(threshold, render_view, "UnstructuredGridRepresentation")
            threshold_display.Representation = "Surface"
            threshold_display.SetScalarBarVisibility(render_view, True)

            if i + 1 < len(registration_names):
                Hide(threshold, render_view)

    # Misc
    # potentialLUT = GetColorTransferFunction("potential")
    # potentialPWF = GetOpacityTransferFunction("potential")
    # potentialTF2D = GetTransferFunction2D("potential")


# UPDATE LAYOUT
layout = GetLayout()
layout.SetSize(720, 650)

# RE-RENDER VIEW
# Get simulation box
if simulation_root_name:
    try:
        path_to_simulation_json = f"{data_folder}/{simulation_root_name}.json"

        with open(path_to_simulation_json, "r") as f:
            data = json.load(f)
            f.close

        current_box = GetActiveSource().GetDataInformation().GetBounds()

        try:
            new_box = {
                "x_min": data["box"]["p1"]["x"] / 1e6,
                "y_min": data["box"]["p1"]["y"] / 1e6,
                "x_max": data["box"]["p2"]["x"] / 1e6,
                "y_max": data["box"]["p2"]["y"] / 1e6,
                "z_min": current_box[4],
                "z_max": current_box[5],
            }
        except KeyError as e:
            new_box = {
                "x_min": data["parameters"]["source_box"]["p1"]["x"] / 1e6,
                "y_min": data["parameters"]["source_box"]["p1"]["y"] / 1e6,
                "x_max": data["parameters"]["source_box"]["p2"]["x"] / 1e6,
                "y_max": data["parameters"]["source_box"]["p2"]["y"] / 1e6,
                "z_min": current_box[4],
                "z_max": current_box[5],
            }

    except (FileNotFoundError, ValueError, KeyError) as e:
        print("Failed to zoom automatically. Not a critical error.")

render_view.ResetActiveCameraToNegativeZ()
if new_box:
    if not cross_section:
        render_view.ResetCamera(
            new_box["x_min"],
            new_box["x_max"],
            new_box["y_min"],
            new_box["y_max"],
            new_box["z_min"],
            new_box["z_max"],
            True,
            0.9,
        )
    else:
        render_view.ResetCamera(True, 0.8)
        render_view.ResetCamera(True, (new_box["y_max"] / new_box["x_max"]) / 2)
        render_view.CameraFocalPoint = [3 * new_box["x_max"], 0, 0]

else:
    render_view.ResetCamera(True, 0.9)
render_view.Update()
