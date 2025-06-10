# This file contains a .py "macro" that runs from within ParaView.
# Note. The file uses dependencies that are NOT KQCircuits dependencies because it runs from within ParaView.
# If you use VSCode, you can disable python analysis warnings by adding the following to your `.vscode/settings.json`:
#   ```
#   { "python.analysis.ignore": [ "**/paraview_macro.py"] }
#   ```

import re
import sys
import json
from pathlib import Path
from paraview.simple import *


def load_data(data_files: list[str]):
    """Loads the foundational data from .pvtu or .vtu files, and returns parameters useful for other functions."""

    simulation_folder_path = str(Path.cwd())
    registration_names = []
    simulation_name = vtu_pvtu = new_box = None

    if data_files:
        simulation_name = "" if not data_files else data_files[0].split("/")[0]
        registration_names = [f.rsplit("/")[1].split(".")[0] for f in data_files]
        vtu_pvtu = data_files[0].rsplit(".")[1]

        if vtu_pvtu == "pvtu":
            for i in range(len(registration_names)):
                reader = XMLPartitionedUnstructuredGridReader(
                    FileName=[simulation_folder_path + "/" + data_files[i]], registrationName=registration_names[i]
                )
        elif vtu_pvtu == "vtu":
            for i in range(len(registration_names)):
                reader = XMLUnstructuredGridReader(
                    FileName=[simulation_folder_path + "/" + data_files[i]], registrationName=registration_names[i]
                )
        reader.TimeArray = "None"

    return simulation_folder_path, simulation_name, registration_names, vtu_pvtu


def format_data(registration_names: list[str], vtu_pvtu: str, cross_section: bool, render_view: object):
    """Formats the foundational data layers."""

    for i in range(len(registration_names)):
        parent = FindSource(registration_names[i])

        if vtu_pvtu == "pvtu":
            parent.TimeArray = "None"

        display = Show(parent, render_view, "UnstructuredGridRepresentation")
        display.Representation = "Surface"
        display.EdgeColor = (1.0, 1.0, 0.0)
        display.Opacity = 0.2 if vtu_pvtu == "pvtu" else 1

        if cross_section or vtu_pvtu == "vtu":
            ColorBy(display, ("POINTS", "potential"))
        else:
            display.SetScalarBarVisibility(render_view, True)

        if i + 1 < len(registration_names) or not cross_section:
            Hide(parent, render_view)


def get_thresholds(sif_files: list[str]) -> list[int]:
    """Determines lower and upper thresholds using .sif file."""

    if sif_files:
        try:
            sif_file_path = Path(Path(Path.cwd()) / sif_files[0])
            with open(sif_file_path, "r") as f:
                sif_contents = f.read()
            pattern = r"(?<=Body\s)\d*\n\s*Target\sBodies\(\d*\).*(?=substrate_1.*\n)"
            matches = re.findall(pattern, sif_contents)
            thresholds = [int(matches[0][0]), int(matches[0][0]) + len(matches) - 1]
        except (ValueError, NameError, TypeError, FileNotFoundError) as e:
            thresholds = []
    return thresholds


def apply_thresholds(
    registration_names: list[str], vtu_pvtu: str, cross_section: bool, thresholds: list[int], render_view: object
):
    """Formats thresholds with information from get_thresholds."""

    if (vtu_pvtu == "pvtu" and thresholds) or not (cross_section and thresholds):
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


def render_data(simulation_folder_path: str, simulation_name: str, cross_section: bool, render_view: object):

    layout = GetLayout()
    layout.SetSize(720, 650)

    new_box = []
    if simulation_name:
        try:
            path_to_simulation_json = f"{simulation_folder_path}/{simulation_name}.json"
            with open(path_to_simulation_json, "r") as f:
                data = json.load(f)
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


def run_macro(data_files: list[str], sif_files: list[str], cross_section: bool):
    """Calls other functions to run applicable parts of a ParaView visualisation."""

    paraview.simple._DisableFirstRenderCameraReset()
    render_view = GetActiveViewOrCreate("RenderView")

    if data_files:
        simulation_folder_path, simulation_name, registration_names, vtu_pvtu = load_data(data_files)
        format_data(registration_names, vtu_pvtu, cross_section, render_view)
    else:
        raise FileNotFoundError("Error with ParaView pipeline. No data files to visualise.")

    if data_files:
        if not cross_section:
            thresholds = get_thresholds(sif_files)
            apply_thresholds(registration_names, vtu_pvtu, cross_section, thresholds, render_view)
        render_data(simulation_folder_path, simulation_name, cross_section, render_view)

    Render()
    Interact()


run_macro(json.loads(sys.argv[1]), json.loads(sys.argv[2]), json.loads(sys.argv[3]))
