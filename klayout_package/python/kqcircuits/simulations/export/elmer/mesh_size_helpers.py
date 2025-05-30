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


def refine_metal_edges(
    size: float = 5.0,
    slope: float = 0.3,
    excitation: int = -1,
    region: str = "",
    ignore_region: str = "",
    face_id: str = "*",
):
    """Returns the mesh_size dictionary to refine the Gmsh mesh at base metal edges.

    This function is useful for most Elmer 3d simulations. The field usually concentrates near the base metal edges, so
    it's beneficial to refine the mesh there.

    The default value for slope argument is chosen to be suitable for typical capacitance or EPR simulations.
    Make sure that the size value match the requirements of your simulation.

    Typical usage is to pass parameter mesh_size=refine_metal_edges(size) for a 3d ElmerSolution. Do not use this
    function with ElmerCrossSectionSolution.

    Args:
        size: mesh element length at base-metal edges [µm]
        slope: determines how fast the mesh element length can increase outside the edge [µm/µm] (0 < slope <= 1)
        excitation: metal excitation value where the refinement is applied, or -1 to cover all excitations
        region: partition region name in which the refinement is applied, or empty string to cover all regions
        ignore_region: partition region name in which the refinement is ignored, or empty string to not use limitation
        face_id: the string face id where the refinement is applied, or * to cover all faces

    """

    metals = ["ground", "signal_*"] if excitation < 0 else ["ground" if excitation == 0 else f"signal_{excitation}"]

    intersections = [f"{face_id}_gap"]
    if region:
        intersections.append(f"*{region}")
    if ignore_region:
        intersections.append(f"!*{ignore_region}")

    return {"&".join([f"{face_id}_{metal}"] + intersections): [size, size, slope] for metal in metals}
