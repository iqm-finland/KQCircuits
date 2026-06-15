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

import sys
import types

import pytest

NON_SIM_DIRS = ["scripts", "log_files", "elmer_data", "s_matrix_plots"]


@pytest.fixture
def cleaned_simulations(monkeypatch):
    """Record the folder names that `elmer_cleanup.py` passes to `delete_meshes`.

    `delete_meshes` itself lives in the core `elmer_helpers` module, so here it is replaced by a recorder. This
    keeps the test focused on the responsibility of the script: choosing which folders to clean.
    """
    cleaned = []
    fake_elmer_helpers = types.ModuleType("elmer_helpers")
    fake_elmer_helpers.delete_meshes = lambda path, simname: cleaned.append(simname)
    monkeypatch.setitem(sys.modules, "elmer_helpers", fake_elmer_helpers)
    return cleaned


def test_cleans_simulation_folders(run_post_process, sim_folder, cleaned_simulations):
    (sim_folder / "waveguides_n_guides_1").mkdir()
    (sim_folder / "waveguides_n_guides_2").mkdir()

    run_post_process("elmer_cleanup.py")

    assert sorted(cleaned_simulations) == ["waveguides_n_guides_1", "waveguides_n_guides_2"]


def test_skips_non_simulation_folders(run_post_process, sim_folder, cleaned_simulations):
    (sim_folder / "waveguides_n_guides_1").mkdir()
    for non_sim_dir in NON_SIM_DIRS:
        (sim_folder / non_sim_dir).mkdir()

    run_post_process("elmer_cleanup.py")

    assert cleaned_simulations == ["waveguides_n_guides_1"]


def test_ignores_files_in_folder(run_post_process, sim_folder, cleaned_simulations):
    (sim_folder / "waveguides_n_guides_1").mkdir()
    (sim_folder / "waveguides_n_guides_1.json").write_text("{}", encoding="utf-8")

    run_post_process("elmer_cleanup.py")

    assert cleaned_simulations == ["waveguides_n_guides_1"]
