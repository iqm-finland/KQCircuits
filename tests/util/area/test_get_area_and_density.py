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

import pytest
from kqcircuits.klayout_view import KLayoutView
from kqcircuits.chips.demo import Demo
from kqcircuits.util.area import get_area_and_density
from kqcircuits.defaults import default_faces


@pytest.fixture
def view():
    return KLayoutView()


@pytest.fixture
def demo_chip_cell(view):
    """Returns a Demo chip cell, with grid enabled and layers merged"""
    inst, _ = view.insert_cell(Demo, with_grid=True, merge_base_metal_gap=True)
    return inst.cell


def test_get_area_and_density_ground_grid_optimization(demo_chip_cell):
    """Compare optimized and non-optimized area calculation results"""
    layer_infos = [default_faces["1t1"][layer] for layer in ["ground_grid", "base_metal_gap", "base_metal_gap_wo_grid"]]

    normal_results = get_area_and_density(demo_chip_cell, layer_infos, optimize_ground_grid_calculations=False)
    optimized_results = get_area_and_density(demo_chip_cell, layer_infos, optimize_ground_grid_calculations=True)

    for face in ["1t1"]:
        assert normal_results[f"{face}_base_metal_gap_wo_grid"] == optimized_results[f"{face}_base_metal_gap_wo_grid"]
        assert normal_results[f"{face}_ground_grid"] == optimized_results[f"{face}_ground_grid"]

    assert (
        abs(1 - normal_results[f"{face}_base_metal_gap"]["area"] / optimized_results[f"{face}_base_metal_gap"]["area"])
        < 1e-4
    )
    assert (
        abs(
            1
            - normal_results[f"{face}_base_metal_gap"]["density"]
            / optimized_results[f"{face}_base_metal_gap"]["density"]
        )
        < 1e-4
    )
