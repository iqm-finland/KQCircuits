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

import csv
import json
import runpy
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
POST_PROCESS_DIR = REPO_ROOT / "klayout_package" / "python" / "scripts" / "simulations" / "post_process"


def _write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def _read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as csvfile:
        return list(csv.DictReader(csvfile))


def _run_post_process(monkeypatch, tmp_path, script_name, *args):
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(POST_PROCESS_DIR))
    script_path = POST_PROCESS_DIR / script_name
    monkeypatch.setattr(sys, "argv", [str(script_path), *map(str, args)])
    runpy.run_path(str(script_path), run_name="__main__")


def test_produce_z0_table_writes_waveguide_parameters(monkeypatch, tmp_path):
    _write_json(tmp_path / "single_project_results.json", {"Cs": [[4.0]], "Ls": [[9.0]]})
    _write_json(tmp_path / "single.json", {"parameters": {"width": 10}})

    _run_post_process(monkeypatch, tmp_path, "produce_z0_table.py")

    rows = _read_csv(tmp_path / f"{tmp_path.name}_Z0.csv")
    assert rows == [
        {
            "key": "single",
            "Cs": "4.0",
            "Ls": "9.0",
            "Z0": "1.5",
            "c_eff": str(1 / 6),
        }
    ]


def test_produce_cmatrix_table_writes_capacitance_matrix(monkeypatch, tmp_path):
    _write_json(tmp_path / "cap_project_results.json", {"CMatrix": [[1.0, 2.0], [3.0, 4.0]]})
    _write_json(tmp_path / "cap.json", {"parameters": {"width": 10}, "tool": "capacitance", "ports": []})

    _run_post_process(monkeypatch, tmp_path, "produce_cmatrix_table.py")

    rows = _read_csv(tmp_path / f"{tmp_path.name}_results.csv")
    assert rows == [
        {
            "key": "cap",
            "C11": "1.0",
            "C12": "2.0",
            "C21": "3.0",
            "C22": "4.0",
        }
    ]


def test_produce_q_factor_table_converts_epr_losses_to_q_factors(monkeypatch, tmp_path):
    _write_json(tmp_path / "loss_tangents.json", {"ma": 1e-6, "substrate": 2e-6})
    _write_json(tmp_path / "sample_project_results.json", {})
    _write_json(tmp_path / "sample.json", {"parameters": {"width": 10}})
    (tmp_path / "sample_epr.csv").write_text(
        "key,p_ma,p_substrate,E_total\n" "sample,0.25,0.5,1.0\n",
        encoding="utf-8",
    )

    _run_post_process(monkeypatch, tmp_path, "produce_q_factor_table.py", tmp_path / "loss_tangents.json")

    rows = _read_csv(tmp_path / "sample_q_factors.csv")
    assert rows[0]["key"] == "sample"
    assert float(rows[0]["Q_ma"]) == pytest.approx(4_000_000)
    assert float(rows[0]["Q_substrate"]) == pytest.approx(1_000_000)
    assert float(rows[0]["Q_total"]) == pytest.approx(800_000)


def test_elmer_profiler_writes_runtime_and_mesh_statistics(monkeypatch, tmp_path):
    (tmp_path / "log_files").mkdir()
    (tmp_path / "sample_mesh").mkdir()
    _write_json(tmp_path / "sample_project_results.json", {})
    _write_json(
        tmp_path / "sample.json",
        {
            "parameters": {"width": 10},
            "mesh_name": "sample_mesh",
            "workflow": {"elmer_n_processes": 2, "elmer_n_threads": 3, "gmsh_n_threads": 4},
        },
    )
    (tmp_path / "log_files" / "sample_mesh.Gmsh.log").write_text(
        "Info    : Done meshing 1D (Wall 0.10, CPU 0.20)\n" "Info    : Done meshing 2D (Wall 0.30, CPU 0.40)\n",
        encoding="utf-8",
    )
    (tmp_path / "log_files" / "sample.Elmer.log").write_text(
        "SOLVER TOTAL TIME(CPU,REAL): 3.0 4.0\n",
        encoding="utf-8",
    )
    (tmp_path / "sample_mesh" / "mesh.header").write_text("10 42 0\n", encoding="utf-8")

    _run_post_process(monkeypatch, tmp_path, "elmer_profiler.py")

    rows = _read_csv(tmp_path / f"{tmp_path.name}_profile.csv")
    assert rows[0]["key"] == "sample"
    assert rows[0]["elmer_n_processes"] == "2"
    assert rows[0]["elmer_n_threads"] == "3"
    assert rows[0]["gmsh_n_threads"] == "4"
    assert float(rows[0]["gmsh_time_real"]) == pytest.approx(0.4)
    assert float(rows[0]["gmsh_time_cpu"]) == pytest.approx(0.6)
    assert float(rows[0]["elmer_time_cpu"]) == pytest.approx(6.0)
    assert float(rows[0]["elmer_time_real"]) == pytest.approx(4.0)
    assert rows[0]["elmer_elements"] == "42"


def test_elmer_cleanup_skips_non_simulation_directories(monkeypatch, tmp_path):
    cleaned = []
    fake_elmer_helpers = types.ModuleType("elmer_helpers")
    fake_elmer_helpers.delete_meshes = lambda path, simname: cleaned.append((Path(path), simname))
    monkeypatch.setitem(sys.modules, "elmer_helpers", fake_elmer_helpers)

    for directory in ("scripts", "log_files", "elmer_data", "s_matrix_plots", "simulation_a"):
        (tmp_path / directory).mkdir()

    _run_post_process(monkeypatch, tmp_path, "elmer_cleanup.py")

    assert cleaned == [(tmp_path, "simulation_a")]
