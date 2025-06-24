# This code is part of KQCircuits
# Copyright (C) 2025 IQM Finland Oy
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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).

# This file contains a .py "macro" that runs from within ParaView.
# Note. The file uses dependencies that are NOT KQCircuits dependencies because it runs from within ParaView.
# If you use VSCode, you can disable python analysis warnings by adding the following to your `.vscode/settings.json`:
#   ```
#   { "python.analysis.ignore": [ "**/paraview_macro.py"] }
#   ```

import logging
import re
import json
from pathlib import Path
from paraview.simple import *  # pylint: disable=wildcard-import


def format_data(registration_names: list[str], vtu_pvtu: str, cross_section: bool, render_view: object):
    """Formats the foundational data layers."""

    for i, registration_name in enumerate(registration_names):
        parent = FindSource(registration_name)  # pylint: disable=undefined-variable

        if vtu_pvtu == "pvtu":
            parent.TimeArray = "None"

        display = Show(parent, render_view, "UnstructuredGridRepresentation")  # pylint: disable=undefined-variable
        display.Representation = "Surface"
        display.EdgeColor = (1.0, 1.0, 0.0)
        display.Opacity = 0.2 if vtu_pvtu == "pvtu" else 1

        if cross_section or vtu_pvtu == "vtu":
            ColorBy(display, ("POINTS", "potential"))  # pylint: disable=undefined-variable
        else:
            display.SetScalarBarVisibility(render_view, True)

        if i + 1 < len(registration_names) or not cross_section:
            Hide(parent, render_view)  # pylint: disable=undefined-variable


def get_thresholds(sif_files: list[str]) -> list[int]:
    """Determines lower and upper thresholds using .sif file."""

    if sif_files:
        try:
            sif_file_path = Path(Path(Path.cwd()) / sif_files[0])
            with open(sif_file_path, "r", encoding="utf-8") as f:
                sif_contents = f.read()
            pattern = r"(?<=Body\s)(\d*\n*)(.*\s){0,4}Target\sBodies\(\d*\).*(?=substrate_1.*\n)"
            matches = re.findall(pattern, sif_contents)
            thresholds = [int(matches[0][0]), int(matches[0][0]) + len(matches) - 1]
        except (ValueError, NameError, TypeError, FileNotFoundError):
            thresholds = []
        return thresholds
    return None


def apply_thresholds(
    registration_names: list[str], vtu_pvtu: str, cross_section: bool, thresholds: list[int], render_view: object
):
    """Formats thresholds with information from get_thresholds."""

    if (vtu_pvtu == "pvtu" and thresholds) or not (cross_section and thresholds):
        for i, registration_name in enumerate(registration_names):
            parent = FindSource(registration_name)  # pylint: disable=undefined-variable
            # pylint: disable=undefined-variable
            threshold = Threshold(registrationName=f"{registration_name}-threshold", Input=parent)
            threshold.ThresholdMethod = "Between"
            threshold.LowerThreshold = thresholds[0]
            threshold.UpperThreshold = thresholds[1]
            threshold.Scalars = ["CELLS", "GeometryIds"]
            # pylint: disable=undefined-variable
            threshold_display = Show(threshold, render_view, "UnstructuredGridRepresentation")
            threshold_display.Representation = "Surface"
            threshold_display.SetScalarBarVisibility(render_view, True)

            if i + 1 < len(registration_names):
                Hide(threshold, render_view)  # pylint: disable=undefined-variable


def render_data(simulation_folder_path: str, simulation_name: str, cross_section: bool, render_view: object):

    layout = GetLayout()  # pylint: disable=undefined-variable
    layout.SetSize(720, 650)

    new_box = []
    if simulation_name:
        try:
            path_to_simulation_json = f"{simulation_folder_path}/{simulation_name}.json"
            with open(path_to_simulation_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            current_box = GetActiveSource().GetDataInformation().GetBounds()  # pylint: disable=undefined-variable
            try:
                new_box = {
                    "x_min": data["box"]["p1"]["x"] / 1e6,
                    "y_min": data["box"]["p1"]["y"] / 1e6,
                    "x_max": data["box"]["p2"]["x"] / 1e6,
                    "y_max": data["box"]["p2"]["y"] / 1e6,
                    "z_min": current_box[4],
                    "z_max": current_box[5],
                }
            except KeyError:
                new_box = {
                    "x_min": data["parameters"]["source_box"]["p1"]["x"] / 1e6,
                    "y_min": data["parameters"]["source_box"]["p1"]["y"] / 1e6,
                    "x_max": data["parameters"]["source_box"]["p2"]["x"] / 1e6,
                    "y_max": data["parameters"]["source_box"]["p2"]["y"] / 1e6,
                    "z_min": current_box[4],
                    "z_max": current_box[5],
                }
        except (FileNotFoundError, ValueError, KeyError):
            logging.warning("Failed to zoom automatically. Not a critical error.")

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

    paraview.simple._DisableFirstRenderCameraReset()  # pylint: disable=undefined-variable
    render_view = GetActiveViewOrCreate("RenderView")  # pylint: disable=undefined-variable

    simulation_folder_path = str(Path.cwd())
    registration_names = []
    simulation_name, vtu_pvtu = None, None
    if data_files:
        simulation_name = Path(data_files[0]).parent
        registration_names = [Path(f).name for f in data_files]
        vtu_pvtu = "pvtu" if ".pvtu" in data_files[0] else "vtu"
        format_data(registration_names, vtu_pvtu, cross_section, render_view)
    else:
        raise FileNotFoundError("Error with ParaView automation. No data files passed to macro.")

    if data_files:
        if not cross_section:
            thresholds = get_thresholds(sif_files)
            apply_thresholds(registration_names, vtu_pvtu, cross_section, thresholds, render_view)
        render_data(simulation_folder_path, simulation_name, cross_section, render_view)

    Render()  # pylint: disable=undefined-variable
