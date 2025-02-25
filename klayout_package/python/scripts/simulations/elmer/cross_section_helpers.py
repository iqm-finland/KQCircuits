# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import gmsh
from scipy.constants import mu_0, epsilon_0

from elmer_helpers import (
    sif_capacitance,
    sif_inductance,
    sif_circuit_definitions,
    use_london_equations,
)

from gmsh_helpers import (
    separated_hull_and_holes,
    add_polygon,
    set_mesh_size_field,
    get_recursive_children,
    set_meshing_options,
    apply_elmer_layer_prefix,
    get_metal_layers,
)

try:
    import pya
except ImportError:
    import klayout.db as pya

angular_frequency = 5e2  # a constant for inductance simulations.
# technically is needed but doesn't affect results
# howewer, if very high, might have an unwanted effect


def produce_cross_section_mesh(json_data: dict[str, Any], msh_file: Path | str) -> None:
    """
    Produces 2D cross-section mesh and optionally runs the Gmsh GUI

    Args:
        json_data: all the model data produced by `export_elmer_json`
        msh_file: mesh file name
    """

    if Path(msh_file).exists():
        print(f"Reusing existing mesh from {str(msh_file)}")
        return

    # Initialize gmsh
    gmsh.initialize()

    # Read geometry from gds file
    layout = pya.Layout()
    layout.read(json_data["gds_file"])
    cell = layout.top_cell()
    bbox = cell.bbox()
    layers = json_data["layers"]

    # Create mesh using geometries in gds file
    gmsh.model.add("cross_section")

    dim_tags = {}
    for name, data in layers.items():
        reg = pya.Region(cell.shapes(layout.layer(data["layer"], 0)))
        layer_dim_tags = []
        for simple_poly in reg.each():
            poly = separated_hull_and_holes(simple_poly)
            hull_point_coordinates = [
                (point.x * layout.dbu, point.y * layout.dbu, 0) for point in poly.each_point_hull()
            ]
            hull_plane_surface_id, _ = add_polygon(hull_point_coordinates)
            hull_dim_tag = (2, hull_plane_surface_id)
            hole_dim_tags = []
            for hole in range(poly.holes()):
                hole_point_coordinates = [
                    (point.x * layout.dbu, point.y * layout.dbu, 0) for point in poly.each_point_hole(hole)
                ]
                hole_plane_surface_id, _ = add_polygon(hole_point_coordinates)
                hole_dim_tags.append((2, hole_plane_surface_id))
            if hole_dim_tags:
                layer_dim_tags += gmsh.model.occ.cut([hull_dim_tag], hole_dim_tags)[0]
            else:
                layer_dim_tags.append(hull_dim_tag)
        dim_tags[name] = layer_dim_tags

    # Call fragment and get updated dim_tags as new_tags. Then synchronize.
    all_dim_tags = [tag for tags in dim_tags.values() for tag in tags]
    _, dim_tags_map_imp = gmsh.model.occ.fragment(all_dim_tags, [], removeTool=False)
    dim_tags_map = dict(zip(all_dim_tags, dim_tags_map_imp))
    new_tags = {
        name: [new_tag for old_tag in tags for new_tag in dim_tags_map[old_tag]] for name, tags in dim_tags.items()
    }
    gmsh.model.occ.synchronize()

    # Refine mesh
    # Here json_data['mesh_size'] is assumed to be dictionary where key denotes material (string) and value (double)
    # denotes the maximal length of mesh element. Additional terms can be determined, if the value type is list. Then,
    # - term[0] = the maximal mesh element length inside at the entity and its expansion
    # - term[1] = expansion distance in which the maximal mesh element length is constant (default=term[0])
    # - term[2] = the slope of the increase in the maximal mesh element length outside the entity
    #
    # To refine material interface the material names by should be separated by '&' in the key. Key 'global_max' is
    # reserved for setting global maximal element length. For example, if the dictionary is given as
    # {'substrate': 10, 'substrate&vacuum': [2, 5], 'global_max': 100}, then the maximal mesh element length is 10
    # inside the substrate and 2 on region which is less than 5 units away from the substrate-vacuum interface. Outside
    # these regions, the mesh element size can increase up to 100.
    mesh_size = json_data.get("mesh_size", {})
    mesh_global_max_size = mesh_size.pop("global_max", bbox.perimeter())
    mesh_field_ids = []
    for name, size in mesh_size.items():
        intersection: set[tuple[int, int]] = set()
        split_names = name.split("&")
        if all((name in new_tags for name in split_names)):
            for sname in split_names:
                family = get_recursive_children(new_tags[sname]).union(new_tags[sname])
                intersection = intersection.intersection(family) if intersection else family

            mesh_field_ids += set_mesh_size_field(
                list(intersection - get_recursive_children(intersection)),
                mesh_global_max_size,
                *(size if isinstance(size, list) else [size]),
            )
        else:
            print(f'WARNING: No layers corresponding to mesh_size keys "{split_names}" found')

    # Set meshing options
    workflow = json_data.get("workflow", {})
    n_threads_dict = workflow["sbatch_parameters"] if "sbatch_parameters" in workflow else workflow
    gmsh_n_threads = int(n_threads_dict.get("gmsh_n_threads", 1))
    set_meshing_options(mesh_field_ids, mesh_global_max_size, gmsh_n_threads)

    # Add physical groups
    for n in new_tags:
        gmsh.model.addPhysicalGroup(2, [t[1] for t in new_tags[n]], name=apply_elmer_layer_prefix(n))
    metals = [n for n in get_metal_layers(json_data) if n in new_tags]
    for n in metals:
        metal_boundary = gmsh.model.getBoundary(new_tags[n], combined=False, oriented=False, recursive=False)
        gmsh.model.addPhysicalGroup(1, [t[1] for t in metal_boundary], name=f"{apply_elmer_layer_prefix(n)}_boundary")

    set_outer_bcs(bbox, layout)

    # Generate and save mesh
    gmsh.model.mesh.generate(2)
    gmsh.write(str(msh_file))

    # Open mesh viewer
    if workflow.get("run_gmsh_gui", False):
        gmsh.fltk.run()

    gmsh.finalize()


def set_outer_bcs(bbox: pya.DBox, layout: pya.Layout, beps: float = 1e-6) -> None:
    """
    Sets the outer boundaries so that `xmin`, `xmax`, `ymin` and `ymax` can be accessed as physical groups.
    This is a desperate attempt because occ module seems buggy: tried to new draw lines and add them to the
    fragment then fetch the correct `dim_tags`, but the fragment breaks down. So, now we search each boundary
    using a bounding box search.

    Args:
        bbox: bounding box in klayout format
        layout: klayout layout
        beps: tolerance for the search bounding box
    """
    outer_bc_dim_tags = {}
    outer_bc_dim_tags["xmin"] = gmsh.model.occ.getEntitiesInBoundingBox(
        bbox.p1.x * layout.dbu - beps,
        bbox.p1.y * layout.dbu - beps,
        -beps,
        bbox.p1.x * layout.dbu + beps,
        bbox.p2.y * layout.dbu + beps,
        beps,
        dim=1,
    )
    outer_bc_dim_tags["xmax"] = gmsh.model.occ.getEntitiesInBoundingBox(
        bbox.p2.x * layout.dbu - beps,
        bbox.p1.y * layout.dbu - beps,
        -beps,
        bbox.p2.x * layout.dbu + beps,
        bbox.p2.y * layout.dbu + beps,
        beps,
        dim=1,
    )
    outer_bc_dim_tags["ymin"] = gmsh.model.occ.getEntitiesInBoundingBox(
        bbox.p1.x * layout.dbu - beps,
        bbox.p1.y * layout.dbu - beps,
        -beps,
        bbox.p2.x * layout.dbu + beps,
        bbox.p1.y * layout.dbu + beps,
        beps,
        dim=1,
    )
    outer_bc_dim_tags["ymax"] = gmsh.model.occ.getEntitiesInBoundingBox(
        bbox.p1.x * layout.dbu - beps,
        bbox.p2.y * layout.dbu - beps,
        -beps,
        bbox.p2.x * layout.dbu + beps,
        bbox.p2.y * layout.dbu + beps,
        beps,
        dim=1,
    )

    for n, v in outer_bc_dim_tags.items():
        gmsh.model.addPhysicalGroup(1, [t[1] for t in v], name=f"{n}_boundary")


def produce_cross_section_sif_files(json_data: dict[str, Any], folder_path: Path) -> list[str]:
    """
    Produces sif files required for capacitance and inductance simulations.

    Args:
        json_data: all the model data produced by `export_elmer_json`
        folder_path: folder path for the sif files

    Returns:
        sif file paths
    """

    def save(file_name: str, content: str) -> str:
        """Saves file with content given in string format. Returns name of the saved file."""
        with open(Path(folder_path).joinpath(file_name), "w", encoding="utf-8") as f:
            f.write(content)
        return file_name

    folder_path.mkdir(exist_ok=True, parents=True)
    sif_names = json_data["sif_names"]

    sif_files = [
        save(
            f"{sif_names[0]}.sif",
            sif_capacitance(json_data, folder_path, vtu_name=sif_names[0], angular_frequency=0, dim=2, with_zero=False),
        )
    ]
    if json_data["run_inductance_sim"]:
        if use_london_equations(json_data):
            circuit_definitions_file = save("inductance.definitions", sif_circuit_definitions(json_data))
            sif_files.append(
                save(
                    f"{sif_names[1]}.sif",
                    sif_inductance(json_data, folder_path, angular_frequency, circuit_definitions_file),
                )
            )
        else:
            sif_files.append(
                save(
                    f"{sif_names[1]}.sif",
                    sif_capacitance(
                        json_data, folder_path, vtu_name=sif_names[1], angular_frequency=0, dim=2, with_zero=True
                    ),
                )
            )
    return sif_files


def get_cross_section_capacitance_and_inductance(
    json_data: dict[str, Any], folder_path: Path
) -> dict[str, list[list[float]] | None]:
    """
    Returns capacitance and inductance matrices stored in simulation output files.

    Args:
        json_data: all the model data produced by `export_elmer_json`
        folder_path: folder path for the sif files

    Returns:
        Cs and Ls matrices
    """
    try:
        c_matrix_file = Path(folder_path).joinpath("capacitance.dat")
        c_matrix = pd.read_csv(c_matrix_file, sep=r"\s+", header=None).values
    except FileNotFoundError:
        return {"Cs": None, "Ls": None}

    try:
        if use_london_equations(json_data):
            l_matrix_file_name = "inductance.dat"
            l_matrix_file = Path(folder_path).joinpath(l_matrix_file_name)
            if not l_matrix_file.is_file():
                l_matrix_file = Path(folder_path).joinpath(f"{l_matrix_file_name}.0")
            data = pd.read_csv(l_matrix_file, sep=r"\s+", header=None)
            l_matrix_file = Path(folder_path).joinpath(l_matrix_file_name)
            with open(f"{l_matrix_file}.names", encoding="utf-8") as names:
                data.columns = [
                    line.split("res: ")[1].replace("\n", "") for line in names.readlines() if "res:" in line
                ]
            voltage = data["v_component(1) re"] + 1.0j * data["v_component(1) im"]
            current = data["i_component(1) re"] + 1.0j * data["i_component(1) im"]
            impedance = voltage / current
            l_matrix = np.array([np.imag(impedance) / angular_frequency])
        else:
            c0_matrix_file = Path(folder_path).joinpath("capacitance0.dat")
            c0_matrix = pd.read_csv(c0_matrix_file, sep=r"\s+", header=None).values
            l_matrix = mu_0 * epsilon_0 * np.linalg.inv(c0_matrix)
    except FileNotFoundError:
        return {"Cs": c_matrix.tolist(), "Ls": None}

    return {"Cs": c_matrix.tolist(), "Ls": l_matrix.tolist()}
