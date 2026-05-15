# This code is part of KQCircuits
# Copyright (C) 2026 IQM Finland Oy
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
"""
Post process script to sample 3D points of the simulations for following distributions:

- MA interface layer:
sample uniform 2D point near the metal edge and project to the middle height of MA layer

- MS interface layer:
sample unifrom 2D point near the metal edge and project to the middle height of MS layer

- SA interface layer:
sample uniform 2D point near the metal edge and project to the middle height of SA layer

Exported simulation needs to have a non-zero ``metal_height`` parameter value.

The interface layer thicknesses can be set in the simulation script using parameter
``tls_layer_thickness=[ma_thickness, ms_thickness, sa_thickness]``. Alternatively, the thicknesses can be
provided as an argument for this script: ``--thickness-if``, where ``if`` in ``{ma, ms, sa}``.
Note that setting non-zero ``tls_layer_thickness`` causes realistic interface layers to generate which hinders the
simulation performance unless the parameter ``tls_sheet_approximation=True`` is also used.

Use -h argument to read about available arguments for the script. Number of samples, sampling box boundaries and
further sampling options can be configured using arguments.

This script can be reused without re-exporting the simulation if the points need to be resampled.
"""

import argparse
import os
import json
import sys
from typing import Union
import klayout.db
import numpy as np

# Find data files
path = os.path.curdir
files = [f for f in os.listdir(path) if f.endswith("_project_results.json")]
files = [f.replace("_project_results.json", ".json") for f in files]
if not files:
    files = [f for f in os.listdir(path) if f.endswith(".gds")]
    files = [f.replace(".gds", ".json") for f in files]
    if not files:
        print("No suitable simulation files detected.")
        sys.exit()
    print("No '_project_results.json' files detected. Will sample MC points for each .gds file")


def extract_metal_edge_points(points: np.ndarray, metal_edge_step: float):
    """Calculate equidistant points along the perimeter defined by a list of points.

    Args:
        points: ndarray of shape (n, 2) with polygon points.
        metal_edge_step: distance between consecutive spaced points.

    Returns:
        metal_edge_points: list of 2D points equally spaced over the metal edge.
    """
    points = np.vstack([points, points[0]])  # circular boundary condition

    distances = [np.linalg.norm(p1 - p2) for p1, p2 in zip(points, points[1:])]
    cumdist = np.cumsum([0] + distances)
    total_length = cumdist[-1]
    metal_edge_points = []
    for i in range(int(total_length / metal_edge_step)):
        target_dist = (i + 1) * metal_edge_step
        seg_idx = np.searchsorted(cumdist, target_dist) - 1
        pt1 = points[seg_idx]
        pt2 = points[seg_idx + 1]
        # Distance within this segment
        dist_in_segment = target_dist - cumdist[seg_idx]
        segment_length = distances[seg_idx]
        t = dist_in_segment / segment_length
        # Interpolate
        dx = t * (pt2[0] - pt1[0])
        dy = t * (pt2[1] - pt1[1])
        metal_edge_points.append(pt1 + (dx, dy))
    return metal_edge_points


def sample_from_normal(depth: float, metal_edge_points: list):
    """For each input point, returns another point from the
    normal to the segment connecting the previous and subsequent
    point in the list.

    Args:
        depth: distance between input and output points
        metal_edge_points: list of 2D points

    Returns:
        sampled_points_in_depth: list of 2D points
        sampled accordingly.
    """
    sampled_points_in_depth = []
    for i, pt in enumerate(metal_edge_points):
        # Wrap around for closed polygon
        prev_idx = (i - 1) % len(metal_edge_points)
        next_idx = (i + 1) % len(metal_edge_points)
        pt_prev = metal_edge_points[prev_idx]
        pt_next = metal_edge_points[next_idx]

        dx1 = pt[0] - pt_prev[0]
        dy1 = pt[1] - pt_prev[1]
        angle1 = np.atan2(dy1, dx1)

        dx2 = pt_next[0] - pt[0]
        dy2 = pt_next[1] - pt[1]
        angle2 = np.atan2(dy2, dx2)
        # Average the direction vectors
        u1_x, u1_y = np.cos(angle1), np.sin(angle1)
        u2_x, u2_y = np.cos(angle2), np.sin(angle2)
        avg_x = u1_x + u2_x
        avg_y = u1_y + u2_y
        # Normalize
        avg_mag = np.sqrt(avg_x**2 + avg_y**2)
        avg_x /= avg_mag
        avg_y /= avg_mag
        # Rotate 90° counterclockwise to get outward normal
        normal_x = -avg_y
        normal_y = avg_x
        # Offset point
        pt_new = pt + (normal_x * depth, normal_y * depth)
        sampled_points_in_depth.append(pt_new)
    return sampled_points_in_depth


def is_box_polygon(points: np.ndarray, metadata: dict) -> bool:
    """Check whether points contain all boundary-box corners.

    Args:
        points: ndarray of shape (n, 2) with polygon points.
        metadata: dict with box_x1, box_x2, box_y1, box_y2.

    Returns:
        True if all 4 box corners are present in points.
    """

    x1 = metadata["box_x1"]
    x2 = metadata["box_x2"]
    y1 = metadata["box_y1"]
    y2 = metadata["box_y2"]

    corners = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]])

    return all(np.any(np.isclose(points, corner).all(axis=1)) for corner in corners)


def is_within_simulation_boundaries(point: Union[dict, tuple], simulation_box: list):
    """Check whether a point falls inside the simulation box.
    Args:
        point: dict or tuple of (x, y) coordinates
        simulation_box: list of coordinates defining a box.

    Returns:
        Corresponding boolean.
    """
    if isinstance(point, dict):
        return (
            point["x"] > simulation_box[0]
            and point["x"] < simulation_box[1]
            and point["y"] > simulation_box[2]
            and point["y"] < simulation_box[3]
        )
    elif isinstance(point, tuple):
        return (
            point[0] > simulation_box[0]
            and point[0] < simulation_box[1]
            and point[1] > simulation_box[2]
            and point[1] < simulation_box[3]
        )
    else:
        print("WARNING: 'point' can only be of type dict or tuple. Returning 'False'.")
        return False


def populate_around_metal_edges(
    metal_edge_points: list[np.ndarray],
    n_turns: int,
    depth: float,
    z_coordinates: dict,
    vertical_over_etching: float,
    interface_thicknesses: list,
    simulation_box: list,
):
    """Creates list of points for each interface layers around the metal edges.
    Args:
        metal_edge_points: list of points at the metal edges
        n_turns: number of layers sampled inward and outward from the metal edge
        depth: distance between sampled layers
        z_coordinates: dict of z-coordinates for each layer
        vertical_over_etching: vertical over etching parameter (zero when not set)
        interface_thicknesses: list of floats containing the interface layer thicknesses ['ma', 'ms', 'sa']
        simulation_box: list of coordinates defining a box

    Returns:
        Lists of points close to metal edges in each layer.
    """
    sampled_points_ms_3d = []
    sampled_points_ma_3d = []
    sampled_points_sa_3d = []
    sampled_points_ma_wall_3d = []
    sampled_points_sa_wall_3d = []
    # Remove points at the intersection with simulation boundaries
    metal_edge_points = [
        pt for pt in metal_edge_points if is_within_simulation_boundaries((pt[0], pt[1]), simulation_box)
    ]
    sampled_points_ms_ma = metal_edge_points
    sampled_points_sa = metal_edge_points
    for j in range(n_turns):
        sampled_points_ms_ma = sampled_points_ms_ma + sample_from_normal((j + 1) * depth, metal_edge_points)
        sampled_points_sa = sampled_points_sa + sample_from_normal(-(j + 1) * depth, metal_edge_points)

    for sp_ms_ma, sp_sa in zip(sampled_points_ms_ma, sampled_points_sa):
        sampled_points_ms_3d.append({"x": sp_ms_ma[0], "y": sp_ms_ma[1], "z": z_coordinates["z_ms"]})
        sampled_points_ma_3d.append({"x": sp_ms_ma[0], "y": sp_ms_ma[1], "z": z_coordinates["z_ma"]})
        sampled_points_sa_3d.append({"x": sp_sa[0], "y": sp_sa[1], "z": z_coordinates["z_sa"]})
    for sp_ma_wall in sample_from_normal(-interface_thicknesses[0] / 2, metal_edge_points):
        sampled_points_ma_wall_3d.append({"x": sp_ma_wall[0], "y": sp_ma_wall[1], "z": z_coordinates["z_ma_wall"]})
    if vertical_over_etching != 0:
        for sp_sa_wall in sample_from_normal(-interface_thicknesses[2] / 2, metal_edge_points):
            sampled_points_sa_wall_3d.append({"x": sp_sa_wall[0], "y": sp_sa_wall[1], "z": z_coordinates["z_sa_wall"]})

    return (
        sampled_points_ms_3d,
        sampled_points_ma_3d,
        sampled_points_sa_3d,
        sampled_points_ma_wall_3d,
        sampled_points_sa_wall_3d,
    )


parser = argparse.ArgumentParser(description="Point sampler in substrate and near metal edges for TLS")
parser.add_argument("--metal-edge-step", type=float, required=True, help="Sampling step along the metal edge")
parser.add_argument(
    "--n-turns", type=int, default=2, help="Number of layers sampled inward and outward from the metal edge"
)
parser.add_argument("--depth", type=float, default=0.05, help="Distance between sampled layers, unit: µm")
parser.add_argument("--thickness-ma", type=float, default=None, help="Optional: MA layer thickness, unit: µm")
parser.add_argument("--thickness-ms", type=float, default=None, help="Optional: MS layer thickness, unit: µm")
parser.add_argument("--thickness-sa", type=float, default=None, help="Optional: SA layer thickness, unit: µm")
parser.add_argument("--x1", type=int, default=None, help="X position of sample box left boundary in microns")
parser.add_argument("--x2", type=int, default=None, help="X position of sample box right boundary in microns")
parser.add_argument("--y1", type=int, default=None, help="Y position of sample box bottom boundary in microns")
parser.add_argument("--y2", type=int, default=None, help="Y position of sample box top boundary in microns")
args = parser.parse_args()

custom_sample_box = args.x1 is not None and args.x2 is not None and args.y1 is not None and args.y2 is not None
if not custom_sample_box:
    print("Using box parameter of individual simulations to sample points from")


sim_parameters = {}
for file_name in files:
    with open(file_name, encoding="utf-8") as file:
        p = json.load(file)
        if p.get("tool") != "cross-section":
            sim_parameters[file_name] = p

for file_name, parameters in sim_parameters.items():
    # Flatten face_stack
    face_stack = parameters["parameters"]["face_stack"]
    while not all(isinstance(x, str) for x in face_stack):
        new_stack = []
        for x in face_stack:
            if isinstance(x, str):
                new_stack.append(x)
            else:
                new_stack.extend(x)
        face_stack = new_stack

    if custom_sample_box:
        box_x1 = args.x1
        box_x2 = args.x2
        box_y1 = args.y1
        box_y2 = args.y2
    else:
        # Sampling box not specified, use simulation's "box" parameter
        box_x1 = parameters["box"]["p1"]["x"]
        box_x2 = parameters["box"]["p2"]["x"]
        box_y1 = parameters["box"]["p1"]["y"]
        box_y2 = parameters["box"]["p2"]["y"]
    result = {
        "metadata": {
            "metal_edge_step": args.metal_edge_step,
            "n_turns": args.n_turns,
            "depth": args.depth,
            "box_x1": box_x1,
            "box_x2": box_x2,
            "box_y1": box_y1,
            "box_y2": box_y2,
        }
    }
    sheet_distributions = ["ma", "ms", "sa"]

    args_th_l = [getattr(args, f"thickness_{l}") for l in sheet_distributions]
    if not all(args_th_l):
        params_th_l = parameters["parameters"].get("tls_layer_thickness", [])
        if len(params_th_l) != 3 or any(p == 0 for p in params_th_l):
            print(
                f"Some of interface thicknesses {sheet_distributions} not found in simulation parameters"
                f" or given as script arguments. Can't extract monte carlo points from {file_name}"
            )
            continue
        args_th_l = [(th_args if th_args else th_params) for th_args, th_params in zip(args_th_l, params_th_l)]
    layer_thickness = dict(zip(sheet_distributions, args_th_l))

    layout = klayout.db.Layout()
    layout.read(parameters["gds_file"])
    # Prepare Regions for each relevant layer in simulation
    regions = {
        layer_name: (
            klayout.db.Region(layout.begin_shapes(layout.top_cell(), layout.layer(layer_dict["layer"], 0))).merged()
            if "layer" in layer_dict
            else None
        )
        for layer_name, layer_dict in parameters["layers"].items()
    }

    mestep = args.metal_edge_step
    n_turns = args.n_turns
    depth = args.depth
    # Get the simulation boundary on XY
    sim_box = [box_x1, box_x2, box_y1, box_y2]

    for i, face in enumerate(face_stack):
        layer_gap = regions.get(face + "_gap", None)
        if layer_gap is None:
            continue
        result[face] = {}
        # extract layer thicknesses based on face
        substrate_i = face[0]
        substrate = parameters["layers"][f"substrate_{substrate_i}"]
        sub_th = parameters["layers"][f"substrate_{substrate_i}"]["thickness"]
        sub_z = parameters["layers"][f"substrate_{substrate_i}"]["z"]
        metal_th = parameters["parameters"]["metal_height"]
        if f"{face}_etch" in parameters["layers"]:
            vertical_over_etching = parameters["layers"][f"{face}_etch"]["thickness"]
        else:
            vertical_over_etching = 0
        if isinstance(metal_th, list):  # in some simulation scripts, metal thickness is passed as a list
            if i < len(metal_th):
                metal_th = metal_th[i]
            else:
                metal_th = metal_th[-1]
        z_coordinates = {}
        if face[1] == "t":
            z_coordinates["z_ma"] = sub_z + sub_th + metal_th + args_th_l[0] / 2
            z_coordinates["z_ms"] = sub_z + sub_th - args_th_l[1] / 2
            z_coordinates["z_ma_wall"] = sub_z + sub_th + metal_th / 2
            z_coordinates["z_sa"] = sub_z + sub_th - args_th_l[2] / 2 - vertical_over_etching
            z_coordinates["z_sa_wall"] = sub_z + sub_th - args_th_l[2] / 2 - vertical_over_etching / 2
        elif face[1] == "b":
            z_coordinates["z_ma"] = sub_z - metal_th - args_th_l[0] / 2
            z_coordinates["z_ms"] = sub_z + args_th_l[1] / 2
            z_coordinates["z_ma_wall"] = sub_z - metal_th / 2
            z_coordinates["z_sa"] = sub_z + args_th_l[2] / 2 + vertical_over_etching
            z_coordinates["z_sa_wall"] = sub_z + args_th_l[2] / 2 + vertical_over_etching / 2
        else:
            print(f"WARNING: invalid face {face}")
            continue

        # Initialize lists of points close to metal edge regions
        sampled_points_ms_3d = []
        sampled_points_ma_3d = []
        sampled_points_sa_3d = []
        sampled_points_ma_wall_3d = []
        sampled_points_sa_wall_3d = []

        for poly_gap in layer_gap:
            points_gap = (
                np.array([(pt.x, pt.y) for pt in poly_gap.each_point_hull()]) * layout.dbu
            )  # each_point_hull() ignores potential holes in the polygon object
            if is_box_polygon(points_gap, result["metadata"]):
                continue
            metal_edge_points = extract_metal_edge_points(points_gap, mestep)
            ms_3d, ma_3d, sa_3d, ma_wall_3d, sa_wall_3d = populate_around_metal_edges(
                metal_edge_points, n_turns, depth, z_coordinates, vertical_over_etching, args_th_l, sim_box
            )
            sampled_points_ms_3d += ms_3d
            sampled_points_ma_3d += ma_3d
            sampled_points_sa_3d += sa_3d
            sampled_points_ma_wall_3d += ma_wall_3d
            sampled_points_sa_wall_3d += sa_wall_3d
            # Recover polygon holes
            if poly_gap.holes() > 0:
                for i in range(poly_gap.holes()):
                    points_gap = np.array([(pt.x, pt.y) for pt in poly_gap.each_point_hole(i)]) * layout.dbu
                    metal_edge_points = extract_metal_edge_points(points_gap, mestep)
                    ms_3d, ma_3d, sa_3d, ma_wall_3d, sa_wall_3d = populate_around_metal_edges(
                        metal_edge_points, n_turns, depth, z_coordinates, vertical_over_etching, args_th_l, sim_box
                    )
                    sampled_points_ms_3d += ms_3d
                    sampled_points_ma_3d += ma_3d
                    sampled_points_sa_3d += sa_3d
                    sampled_points_ma_wall_3d += ma_wall_3d
                    sampled_points_sa_wall_3d += sa_wall_3d

        # Filter out points outside the simulation region
        sampled_points_ms_3d = [pt for pt in sampled_points_ms_3d if is_within_simulation_boundaries(pt, sim_box)]
        sampled_points_ma_3d = [pt for pt in sampled_points_ma_3d if is_within_simulation_boundaries(pt, sim_box)]
        sampled_points_sa_3d = [pt for pt in sampled_points_sa_3d if is_within_simulation_boundaries(pt, sim_box)]

        print(f"Sampled {file_name} metal edge points in {face} MS using {len(sampled_points_ms_3d)} points")
        print(f"Sampled {file_name} metal edge points in {face} SA using {len(sampled_points_sa_3d)} points")
        print(f"Sampled {file_name} metal edge points in {face} MA using {len(sampled_points_ma_3d)} points")
        print(f"Sampled {file_name} metal edge points in {face} MA walls using {len(sampled_points_ma_wall_3d)} points")
        print(f"Sampled {file_name} metal edge points in {face} SA walls using {len(sampled_points_sa_wall_3d)} points")

        result[face]["ms"] = sampled_points_ms_3d
        result[face]["ma"] = sampled_points_ma_3d
        result[face]["sa"] = sampled_points_sa_3d
        result[face]["ma_wall"] = sampled_points_ma_wall_3d
        result[face]["sa_wall"] = sampled_points_sa_wall_3d

    with open(f"{parameters['name']}_tls_me.json", "w", encoding="utf-8") as file:
        json.dump(result, file, indent=4)
