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

export_script_dir = Path(__file__).parent
sys.path.append(str(export_script_dir.parent))
from export_and_run_helper import assert_sim_script, export_and_run_test

generate_ref_results = False  # set to True if you wish to update the
# reference results with what you get from your tests


def test_n_guides_1(tmp_path):
    export_and_run_test(tmp_path, "cpw_cross_section_sim", ["--number-of-cpws", "1"])

    project_ref_info = {
        "project_results_file": "cpw_cross_section_1_0_project_results.json",
        "ref_project_results_file": "test_n_guides_1.json",
        "rtol": 1e-2,
        "atol": 1e-20,
        "ignore_keys": ["E_ground", "E_signal_"],
    }

    assert_sim_script(
        "cpw_cross_section_sim",
        export_script_dir,
        tmp_path,
        project_ref_info,
        generate_ref_results=generate_ref_results,
    )


def test_n_guides_2(tmp_path):
    export_and_run_test(tmp_path, "cpw_cross_section_sim", ["--number-of-cpws", "2"])

    project_ref_info = {
        "project_results_file": "cpw_cross_section_2_0_project_results.json",
        "ref_project_results_file": "test_n_guides_2.json",
        "rtol": 1e-2,
        "atol": 1e-20,
        "ignore_keys": ["E_ground", "E_signal_"],
    }

    assert_sim_script(
        "cpw_cross_section_sim",
        export_script_dir,
        tmp_path,
        project_ref_info,
        generate_ref_results=generate_ref_results,
    )


def test_vertical_over_etching(tmp_path):
    export_and_run_test(tmp_path, "cpw_cross_section_sim", ["--number-of-cpws", "1", "--vertical-over-etching", "10"])

    project_ref_info = {
        "project_results_file": "cpw_cross_section_1_10.0_project_results.json",
        "ref_project_results_file": "test_vertical_over_etching.json",
        "rtol": 1e-2,
        "atol": 1e-20,
        "ignore_keys": ["E_ground", "E_signal_"],
    }
    assert_sim_script(
        "cpw_cross_section_sim",
        export_script_dir,
        tmp_path,
        project_ref_info,
        generate_ref_results=generate_ref_results,
    )


def test_n_guides_1_axisymmetric(tmp_path):
    export_and_run_test(tmp_path, "cpw_cross_section_sim", ["--axisymmetric-test"])

    project_ref_info = {
        "project_results_file": "cpw_cross_section_80_30.0_project_results.json",
        "ref_project_results_file": "test_n_guides_1_axisymmetric.json",
        "rtol": 1e-2,
        "atol": 1e-20,
        "ignore_keys": ["E_ground", "E_signal_"],
    }

    assert_sim_script(
        "cpw_cross_section_sim",
        export_script_dir,
        tmp_path,
        project_ref_info,
        generate_ref_results=generate_ref_results,
    )
