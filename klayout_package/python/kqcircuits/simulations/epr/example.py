# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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

from typing import Callable
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.epr.utils import extract_child_simulation, EPRTarget
from kqcircuits.simulations.partition_region import PartitionRegion
from kqcircuits.simulations.simulation import Simulation

# This is an example Python file that showcases the format of how to define
# partition regions and correction cuts for an individual element (e.g. qubit)
# to calculate EPR.
#
# To allow these geometries to be visualisable in the KLayout GUI app,
# following has to hold for the EPR element you are interested in:
#   * The python script defining the EPR geometries should be placed in this folder
#     (klayout_package/python/kqcircuits/simulations/epr) and the name of the script
#     should be exactly the same as the script that defines the element.
#   * Use ``partition_regions`` and ``correction_cuts`` as the function names.
#   * Include the element in ``kqcircuits.simulations.epr.gui_config``, listing
#     each partition region by name that you'd wish to visualise.


def partition_regions(simulation: EPRTarget, prefix: str = "") -> list[PartitionRegion]:
    """Derives partition regions needed to simulate a single element.
    Function pointer can be either passed to ``get_single_element_sim_class``
    as ``partition_region_function`` argument,
    or a manually implemented ``Simulation`` class could implement
    the ``get_partition_regions`` function such that it calls this function.

    When KLayout is open in GUI mode, the partition region defined here can be
    visualised by enabling the ``_epr_show`` parameter and assigning layers
    for each partition region using ``_epr_part_reg_XXX_layer``.
    For partition regions to be detected in GUI mode, they need to be listed in
    ``kqcircuits.simulations.epr.gui_config``.

    Args:
        simulation: refpoints and parameters of the single element simulation
            are used to derive the partition regions
        prefix: optional prefix differentiates sets of partition regions
            if extracted from multiple elements within ``simulation``

    Returns:
        List of partition regions
    """
    return [
        PartitionRegion(
            name=f"{prefix}1region",
            face=simulation.face_ids[0],
            metal_edge_dimensions=4.0,
            region=pya.DBox(
                simulation.refpoints["base"] - pya.DPoint(simulation.a, simulation.b),
                simulation.refpoints["base"] + pya.DPoint(simulation.a, simulation.b),
            ),
            vertical_dimensions=3.0,
            visualise=True,
        ),
        PartitionRegion(
            name=f"{prefix}2region",
            face=simulation.face_ids[0],
            metal_edge_dimensions=4.0,
            region=pya.DBox(
                simulation.refpoints["coupler"] - pya.DPoint(simulation.a, simulation.b),
                simulation.refpoints["coupler"] + pya.DPoint(simulation.a, simulation.b),
            ),
            vertical_dimensions=3.0,
            visualise=True,
        ),
        PartitionRegion(
            name=f"{prefix}3region",
            face=simulation.face_ids[0],
            metal_edge_dimensions=4.0,
            region=pya.DBox(
                simulation.refpoints["ro"] - pya.DPoint(simulation.a, simulation.b),
                simulation.refpoints["ro"] + pya.DPoint(simulation.a, simulation.b),
            ),
            vertical_dimensions=3.0,
            visualise=True,
        ),
    ]


def correction_cuts(simulation: EPRTarget, prefix: str = "") -> dict[str, dict]:
    """Derives correction cuts for each partition region in a single element.
    This function is meant to be passed to ``get_epr_correction_simulations``
    as ``correction_cuts`` argument. If a composition of multiple such functions
    is needed (for example ``simulation`` contains multiple elements, for each
    we want to calculate EPR), a function can be defined that returns a dict
    consisting of multiple ``correction_cuts`` calls, then that function
    can be passed to ``get_epr_correction_simulations``.

    When KLayout is open in GUI mode, the correction cuts defined here can be
    visualised by enabling the ``_epr_show`` parameter and assigning a layer
    for correction cuts using ``_epr_cross_section_cut_layer``.

    Args:
        simulation: refpoints and parameters of the single element simulation
            are used to derive the partition regions
        prefix: optional prefix differentiates sets of partition regions
            if extracted from multiple elements within ``simulation``

    Returns:
        Configuration dict of correction cuts used by ``get_epr_correction_simulations``
    """
    return {
        f"{prefix}1region": {
            "p1": simulation.refpoints["base"] + pya.DPoint(0, -30),
            "p2": simulation.refpoints["base"] + pya.DPoint(0, 30),
            "metal_edges": [{"x": 20}],
        },
        f"{prefix}2region": {
            "p1": simulation.refpoints["coupler"] + pya.DPoint(simulation.a, -30),
            "p2": simulation.refpoints["coupler"] + pya.DPoint(simulation.a, 30),
            "metal_edges": [{"x": 30}],
        },
        f"{prefix}3region": {
            "p1": simulation.refpoints["ro"] + pya.DPoint(-30, simulation.b),
            "p2": simulation.refpoints["ro"] + pya.DPoint(30, simulation.b),
            "metal_edges": [{"x": 30}],
        },
    }


def extract_from(
    simulation: EPRTarget, refpoint_prefix: str, parameter_remap_function: Callable[[EPRTarget, str], any]
) -> Simulation:
    """To enable reusing ``partition_regions`` and ``correction_cuts`` functions
    for ``simulation`` that is composed of multiple single elements,
    implement ``extract_from`` function like this, where in the last
    list argument all ``simulation`` parameters (note: not refpoints) that were used
    to implement ``partition_regions`` and ``correction_cuts`` are listed.
    """
    return extract_child_simulation(
        simulation,
        refpoint_prefix,
        parameter_remap_function,
        [
            "face_ids",  # Accesses list's index 0
            "a",
            "b",
        ],
    )
