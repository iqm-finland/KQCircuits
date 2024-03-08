# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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
import sys
import pytest

export_script_dir = Path(__file__).parent
sys.path.append(str(export_script_dir.parent))
from export_and_run_helper import assert_sim_script, export_and_run_test

DEFAULT_WAVEGUIDES_COMPARE_ARGS = [
    "--p-element-order",
    "3",
    "--gap-mesh-size",
    "3",
    "--port-mesh-size",
    "3",
    "--global-mesh-size",
    "100.",
    "--n-gmsh-threads",
    "1",
]
generate_ref_results = False  # set to True if you wish to update the
# reference results with what you get from your tests


@pytest.mark.parametrize(
    "project_ref_info",
    [
        {
            "project_results_file": "waveguides_n_guides_1_project_results.json",
            "ref_project_results_file": "test_flip_chip_n_guides_1.json",
            "rtol": 1e-2,
            "atol": 1e-20,
            "ignore_keys": ["E_ground", "E_signal_"],
        },
        {
            "project_results_file": "waveguides_n_guides_2_project_results.json",
            "ref_project_results_file": "test_flip_chip_n_guides_2.json",
            "rtol": 1e-2,
            "atol": 1e-20,
            "ignore_keys": ["E_ground", "E_signal_"],
        },
    ],
    ids=[f"n_guides_{n}" for n in [1, 2]],
)
def test_flip_chip_n_guides_1_2(project_ref_info, tmp_path):
    export_and_run_test(
        tmp_path,
        "waveguides_sim_compare",
        ["--flip-chip", "--n-guides-range", "1", "2"] + DEFAULT_WAVEGUIDES_COMPARE_ARGS,
    )
    assert_sim_script(
        "waveguides_sim_compare",
        export_script_dir,
        tmp_path,
        project_ref_info,
        generate_ref_results=generate_ref_results,
    )


def test_single_face_n_guides_1(tmp_path):
    export_and_run_test(
        tmp_path, "waveguides_sim_compare", ["--n-guides-range", "1", "1"] + DEFAULT_WAVEGUIDES_COMPARE_ARGS
    )

    project_ref_info = {
        "project_results_file": "waveguides_n_guides_1_project_results.json",
        "ref_project_results_file": "test_single_face_n_guides_1.json",
        "rtol": 1e-2,
        "atol": 1e-20,
        "ignore_keys": ["E_ground", "E_signal_"],
    }

    assert_sim_script(
        "waveguides_sim_compare",
        export_script_dir,
        tmp_path,
        project_ref_info,
        generate_ref_results=generate_ref_results,
    )


def test_single_face_internal_port(tmp_path):
    export_and_run_test(
        tmp_path,
        "waveguides_sim_compare",
        ["--no-edge-ports", "--n-guides-range", "1", "1"] + DEFAULT_WAVEGUIDES_COMPARE_ARGS,
    )

    project_ref_info = {
        "project_results_file": "waveguides_n_guides_1_project_results.json",
        "ref_project_results_file": "test_single_face_internal_port.json",
        "rtol": 1e-2,
        "atol": 1e-20,
        "ignore_keys": ["E_ground", "E_signal_"],
    }

    assert_sim_script(
        "waveguides_sim_compare",
        export_script_dir,
        tmp_path,
        project_ref_info,
        generate_ref_results=generate_ref_results,
    )
