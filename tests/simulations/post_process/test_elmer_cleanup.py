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

import runpy
import shutil
import sys
import types
from pathlib import Path


POST_PROCESS_DIR = Path("klayout_package/python/scripts/simulations/post_process")


def _fake_elmer_helpers():
    module = types.ModuleType("elmer_helpers")
    calls = []

    def delete_meshes(path, simname):
        calls.append(simname)
        simulation_dir = path / simname
        (path / f"{simname}.msh").unlink(missing_ok=True)
        for name in ("mesh.nodes", "mesh.elements", "mesh.boundary"):
            (simulation_dir / name).unlink(missing_ok=True)
        for partition_dir in simulation_dir.glob("partitioning.*"):
            if partition_dir.is_dir():
                shutil.rmtree(partition_dir)

    module.delete_meshes = delete_meshes
    module.calls = calls
    return module


def test_elmer_cleanup_deletes_mesh_artifacts_only_from_simulation_dirs(tmp_path, monkeypatch):
    """`elmer_cleanup.py` skips known non-simulation folders and removes mesh artifacts."""
    simulation_dir = tmp_path / "waveguide"
    simulation_dir.mkdir()
    for name in ("mesh.nodes", "mesh.elements", "mesh.boundary"):
        (simulation_dir / name).write_text("mesh data", encoding="utf-8")
    partition_dir = simulation_dir / "partitioning.1"
    partition_dir.mkdir()
    (partition_dir / "part.1").write_text("partition data", encoding="utf-8")
    (tmp_path / "waveguide.msh").write_text("gmsh data", encoding="utf-8")
    (simulation_dir / "capacitance.dat").write_text("keep", encoding="utf-8")

    for non_sim_dir in ("scripts", "log_files", "elmer_data", "s_matrix_plots"):
        path = tmp_path / non_sim_dir
        path.mkdir()
        (path / "mesh.nodes").write_text("keep", encoding="utf-8")
        (path / "partitioning.1").mkdir()

    fake_helpers = _fake_elmer_helpers()
    monkeypatch.setitem(sys.modules, "elmer_helpers", fake_helpers)
    monkeypatch.chdir(tmp_path)
    script_path = Path(__file__).parents[3] / POST_PROCESS_DIR / "elmer_cleanup.py"
    runpy.run_path(str(script_path), run_name="__main__")

    assert fake_helpers.calls == ["waveguide"]
    assert not (tmp_path / "waveguide.msh").exists()
    assert not (simulation_dir / "mesh.nodes").exists()
    assert not (simulation_dir / "mesh.elements").exists()
    assert not (simulation_dir / "mesh.boundary").exists()
    assert not partition_dir.exists()
    assert (simulation_dir / "capacitance.dat").exists()

    for non_sim_dir in ("scripts", "log_files", "elmer_data", "s_matrix_plots"):
        assert (tmp_path / non_sim_dir / "mesh.nodes").exists()
        assert (tmp_path / non_sim_dir / "partitioning.1").exists()


def test_elmer_cleanup_does_not_require_mesh_files_to_exist(tmp_path, monkeypatch):
    """Missing mesh files are acceptable because post-processing can be rerun."""
    simulation_dir = tmp_path / "empty_simulation"
    simulation_dir.mkdir()

    fake_helpers = _fake_elmer_helpers()
    monkeypatch.setitem(sys.modules, "elmer_helpers", fake_helpers)
    monkeypatch.chdir(tmp_path)
    script_path = Path(__file__).parents[3] / POST_PROCESS_DIR / "elmer_cleanup.py"
    runpy.run_path(str(script_path), run_name="__main__")

    assert fake_helpers.calls == ["empty_simulation"]
    assert simulation_dir.exists()
