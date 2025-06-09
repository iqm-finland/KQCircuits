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
"""
Post process script to sample 3D points of the simulations for following distributions:

- MA interface layer:
sample uniform 2D point and project to the middle height of MA layer, reject points outside of metal deposits

- MS interface layer:
sample unifrom 2D point and project to the middle height of MS layer, reject points outside of metal deposits

- SA interface layer:
sample uniform 2D point and project to the middle height of SA layer, reject points outside of gaps

- substrate: sample uniform 3D point according to substrate thickness

Exported simulation needs to have a non-zero ``metal_height`` parameter value and three parameters in
``extra_json_data`` for TLS layer thicknesses in microns: ``ma_thickness``, ``ms_thickness``, ``sa_thickness``.

Use -h argument to read about available arguments for the script. Number of samples, sampling box boundaries and
seed number of the sampler can be configured using arguments.

This script can be reused without re-exporting the simulation if the points need to be resampled.
"""

import argparse
import os
import json
import random
import sys
import klayout.db
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "util"))

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


def get_random_point_from_box(
    rng: random.Random, box_x1: float, box_x2: float, box_y1: float, box_y2: float, dbu: float
) -> tuple[klayout.db.Point, klayout.db.DPoint]:
    """Two independent uniform distributed random variables
    (box_x1 - box_x2), (box_y1 - box_y2) to sample a 2D point.

    Args:
        rng: Random number generator object
        dbu: layout.dbu data base unit to micron coefficient

    Returns:
        point: KLayout integer 2D point object
        dpoint: point converted to micron units, with rounding
    """
    point = klayout.db.DPoint(rng.uniform(box_x1, box_x2), rng.uniform(box_y1, box_y2)).to_itype(dbu)
    return point, point.to_dtype(dbu)


def get_z(
    layers: dict,
    point_in_layers: list[str],
    is_metal_distribution: bool,
    take_top: bool,
    face: str,
    interface_thickness: float,
) -> None | float:
    """Determines z coordinate of 2D point

    Args:
        layers: "layers" object in simulation json file
        point_in_layers: list of layer names that contain the point
        is_metal_distribution: set to True if point sampled from metal regions. Set to False if sampled from substrate.
        take_top: if True, takes the level at the top of deposit. If False, takes the level at the base of deposit.
        face: face id currently being processed
        interface_thickness: thickness of the interface (MA, SA, MS) layer

    Returns:
        z coordinate of the point projected, or None if not applicable
    """
    if is_metal_distribution:
        consider_layers = [l for l in point_in_layers if "excitation" in layers[l] and l.startswith(face)]
    else:
        consider_layers = [l for l in point_in_layers if l == f"{face}_etch"]
        if not consider_layers:
            consider_layers = [l for l in point_in_layers if l == f"{face}_gap"]
    if not consider_layers:
        return None
    add_thickness = take_top == (face[1] == "t")
    zs = [layers[l]["z"] + (layers[l]["thickness"] if add_thickness else 0) for l in consider_layers]
    if len(set(zs)) > 1:
        print("WARNING: multiple z values found")

    # `take_top` indicates MA layer for which we need to sample opposite side of `zs` compared to other interfaces
    sign = -1 if take_top else 1
    if face[1] == "t":
        return max(zs) - sign * interface_thickness / 2.0
    elif face[1] == "b":
        return min(zs) + sign * interface_thickness / 2.0
    else:
        print(f"Unexpected character '{face[1]}' at face {face}")
        return None


def _sample_from_triangle(tri: np.ndarray) -> np.ndarray:
    """
    Uniformly samples a point from a triangle

    Source for the formula:
    https://math.stackexchange.com/questions/18686/uniform-random-point-in-triangle-in-3d

    Args:
        tri: points defining the triangle (array of shape 3x2)

    Returns:
        sampled point (array of shape 1x2)
    """
    r1, r2 = np.random.rand(2)
    sqrt_r1 = np.sqrt(r1)
    point = (1 - sqrt_r1) * tri[0] + sqrt_r1 * (1 - r2) * tri[1] + sqrt_r1 * r2 * tri[2]
    return point


def _sample_from_region(region: klayout.db.Region, n_samples: int, zlims: list[float], dbu: float) -> list[dict]:
    """Samples points uniformly from an arbitrary 2D region using triangulation. Additionally samples
    z-coordinates for each point which is done uniformly and independent of the xy-sampling from `region`.

    Args:
        region: 2D region to sample from
        n_samples: Number of samples to be returned
        zlims: list defining the range for sampling z-coordinates. Should have 2 elements in the order [min, max]
        dbu: Database units used in region

    Returns:
        list of sampled points in dictionary format
    """
    triangles = []
    areas = []
    # Triangulate each polygon in the region
    for poly in region.each():
        for tri in poly.delaunay():
            pts = np.array([[pt.x, pt.y] for pt in tri.each_point_hull()])
            triangles.append(pts)
            areas.append(tri.area())
    areas = np.array(areas)
    probs = areas / areas.sum()
    # sample z independently
    z_sampled = np.random.uniform(low=zlims[0], high=zlims[1], size=n_samples)
    sampled_points = []
    for z in z_sampled:
        # randomly choose a triangle and then point inside the triangle
        tri = triangles[np.random.choice(len(triangles), p=probs)]
        pt = _sample_from_triangle(tri)
        sampled_points.append({"x": pt[0] * dbu, "y": pt[1] * dbu, "z": z})
    return sampled_points


parser = argparse.ArgumentParser(description="Monte carlo point sampler for TLS")
parser.add_argument("--seed", type=int, default=None, help="Specify seed if you want deterministic sampling")
parser.add_argument(
    "--density-ma", type=float, required=True, help="MA TLS sampling volume density, unit: defects/µm^3"
)
parser.add_argument(
    "--density-ms", type=float, required=True, help="MS TLS sampling volume density, unit: defects/µm^3"
)
parser.add_argument(
    "--density-sa", type=float, required=True, help="SA TLS sampling volume density, unit: defects/µm^3"
)
parser.add_argument(
    "--density-substrate", type=float, required=True, help="Substrate sampling volume density, unit: defects/µm^3"
)
parser.add_argument("--x1", type=int, default=None, help="X position of sample box left boundary in microns")
parser.add_argument("--x2", type=int, default=None, help="X position of sample box right boundary in microns")
parser.add_argument("--y1", type=int, default=None, help="Y position of sample box bottom boundary in microns")
parser.add_argument("--y2", type=int, default=None, help="Y position of sample box top boundary in microns")
args = parser.parse_args()

# If seed not specified, make "undeterministic" sampling but log the seed so same sampling can be done deterministically
if args.seed is None:
    seed = random.randrange(sys.maxsize)
else:
    seed = args.seed
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
            "seed": seed,
            "density_ma": args.density_ma,
            "density_ms": args.density_ms,
            "density_sa": args.density_sa,
            "density_substrate": args.density_substrate,
            "box_x1": box_x1,
            "box_x2": box_x2,
            "box_y1": box_y1,
            "box_y2": box_y2,
        }
    }

    sheet_distributions = ["ma", "ms", "sa"]
    extra_json_data = parameters.get("parameters", {}).get("extra_json_data", {})

    if not extra_json_data or any((f"{dist}_thickness" not in extra_json_data for dist in sheet_distributions)):
        print(
            f"some of interface thicknesses {sheet_distributions} missing from extra_json_data, "
            f"can't extract monte carlo points from {file_name}"
        )
        continue

    # Use same seed for all sweeps
    rng = random.Random(seed)
    # Number of sample points = given defect density * sampling box area
    sampling_box_area = (box_x2 - box_x1) * (box_y2 - box_y1)

    tls_n_points = {
        dist: int(getattr(args, f"density_{dist}") * extra_json_data[f"{dist}_thickness"] * sampling_box_area)
        for dist in sheet_distributions
    }

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

    for face in face_stack:
        result[face] = {}
        for distribution in sheet_distributions:
            points = []
            print(
                f"Sampling {file_name} {distribution} TLS layer on face {face} "
                f"using at most {tls_n_points[distribution]} points"
            )
            for _ in range(tls_n_points[distribution]):
                point, dpoint = get_random_point_from_box(rng, box_x1, box_x2, box_y1, box_y2, layout.dbu)
                point_in_layers = set(
                    layer_name
                    for layer_name, region in regions.items()
                    if region is None or any(poly.inside(point) for poly in region.each())
                )
                z = get_z(
                    parameters["layers"],
                    point_in_layers,
                    distribution in ["ma", "ms"],
                    distribution == "ma",
                    face,
                    extra_json_data[f"{distribution}_thickness"],
                )
                # Reject point if sampled outside of region
                if z is not None:
                    points.append({"x": dpoint.x, "y": dpoint.y, "z": z})
            result[face][distribution] = points
        # Fourth, substrate distribution
        substrate_i = face[0]
        substrate = parameters["layers"][f"substrate_{substrate_i}"]
        etch_layer = f"{face}_etch"
        # Number of sample points = given defect density * substrate volume
        substrate_n_points = int(args.density_substrate * sampling_box_area * substrate["thickness"])
        points = []
        print(f"Sampling {file_name} substrate_{substrate_i} using at most {substrate_n_points} points")
        for _ in range(substrate_n_points):
            point, dpoint = get_random_point_from_box(rng, box_x1, box_x2, box_y1, box_y2, layout.dbu)
            z = rng.uniform(substrate["z"], substrate["z"] + substrate["thickness"])
            # Reject point if it is sampled from the over etched part of substrate
            if etch_layer in regions and any(poly.inside(point) for poly in regions[etch_layer].each()):
                if face[1] == "t":
                    if z > parameters["layers"][etch_layer]["z"]:
                        continue
                elif face[1] == "b":
                    if z < parameters["layers"][etch_layer]["z"] + parameters["layers"][etch_layer]["thickness"]:
                        continue
            points.append({"x": dpoint.x, "y": dpoint.y, "z": float(f"{z:.5f}")})
        result[face]["substrate"] = points

        # Sample from gap walls
        gap_region = regions.get(f"{face}_gap")
        if gap_region:
            metal_region = sum(
                (r for l, r in regions.items() if (l.startswith(f"{face}_signal") or l.startswith(f"{face}_ground"))),
                start=klayout.db.Region(),
            )
            # MA wall
            ma_th = extra_json_data["ma_thickness"]
            gap_props = parameters["layers"][f"{face}_gap"]
            ma_wall_region = (metal_region.sized(round(ma_th / layout.dbu)) & gap_region).merged()
            ma_wall_height = ma_th + gap_props["thickness"]
            ma_wall_n_points = round(args.density_ma * ma_wall_region.area() * layout.dbu**2 * ma_wall_height)
            if ma_wall_n_points > 0:
                zlims = [gap_props["z"], gap_props["z"] + gap_props["thickness"]]
                if face[1] == "t":
                    zlims[1] += ma_th
                else:
                    zlims[0] -= ma_th
                print(f"Sampling {file_name} ma wall on face {face} using {ma_wall_n_points} points")
                result[face]["ma_wall"] = _sample_from_region(ma_wall_region, ma_wall_n_points, zlims, layout.dbu)
            # SA wall
            trench_props = parameters["layers"].get(f"{face}_etch")
            if trench_props:
                sa_wall_region = (
                    metal_region.sized(round(extra_json_data["sa_thickness"] / layout.dbu)) & gap_region
                ).merged()
                sa_wall_n_points = round(
                    args.density_sa * sa_wall_region.area() * layout.dbu**2 * trench_props["thickness"]
                )
                if sa_wall_n_points > 0:
                    zlims = [trench_props["z"], trench_props["z"] + trench_props["thickness"]]
                    print(f"Sampling {file_name} sa wall on face {face} using {sa_wall_n_points} points")
                    result[face]["sa_wall"] = _sample_from_region(sa_wall_region, sa_wall_n_points, zlims, layout.dbu)

    with open(f"{parameters['name']}_tls_mc.json", "w", encoding="utf-8") as file:
        json.dump(result, file, indent=4)
