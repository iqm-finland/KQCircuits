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


POST_PROCESS_DIR = Path(__file__).resolve().parents[3] / "klayout_package/python/scripts/simulations/post_process"


def _write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def _run_post_process_script(monkeypatch, tmp_path, script_name):
    script_path = POST_PROCESS_DIR / script_name
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(POST_PROCESS_DIR))
    monkeypatch.setattr(sys, "argv", [str(script_path)])
    runpy.run_path(str(script_path), run_name="__main__")


def _read_single_row(csv_path):
    with csv_path.open(encoding="utf-8", newline="") as csvfile:
        rows = list(csv.DictReader(csvfile))
    assert len(rows) == 1
    return rows[0]


def test_produce_cmatrix_table_writes_capacitance_csv(monkeypatch, tmp_path):
    _write_json(tmp_path / "mock_project_results.json", {"CMatrix": [[1.0, 2.0], [3.0, 4.0]]})
    _write_json(tmp_path / "mock.json", {"parameters": {"width": 10}})

    _run_post_process_script(monkeypatch, tmp_path, "produce_cmatrix_table.py")

    row = _read_single_row(tmp_path / f"{tmp_path.name}_results.csv")
    assert row == {
        "key": "mock",
        "C11": "1.0",
        "C12": "2.0",
        "C21": "3.0",
        "C22": "4.0",
    }


def test_produce_cmatrix_table_applies_cross_section_deembedding(monkeypatch, tmp_path):
    _write_json(tmp_path / "mock_project_results.json", {"CMatrix": [[10.0]]})
    _write_json(
        tmp_path / "mock.json",
        {
            "parameters": {"width": 10},
            "tool": "capacitance",
            "ports": [{"deembed_len": 2.0e6, "deembed_cross_section": "cs"}],
        },
    )
    _write_json(tmp_path / "mock_cs_project_results.json", {"Cs": [[3.0]]})
    _write_json(
        tmp_path / "mock_cs.json",
        {
            "parameters": {"width": 20},
            "tool": "cross-section",
            "layers": {"signal": {"excitation": 1}},
        },
    )

    _run_post_process_script(monkeypatch, tmp_path, "produce_cmatrix_table.py")

    with (tmp_path / f"{tmp_path.name}_results.csv").open(encoding="utf-8", newline="") as csvfile:
        rows = {row["key"]: row for row in csv.DictReader(csvfile)}
    assert rows["mock"] == {
        "key": "mock",
        "width": "10",
        "C11": "4.0",
        "C11_deembed": "6.0",
    }
    assert rows["mock_cs"] == {
        "key": "mock_cs",
        "width": "20",
        "C11": "3.0",
        "C11_deembed": "0.0",
    }


def test_produce_z0_table_writes_waveguide_parameter_csv(monkeypatch, tmp_path):
    _write_json(tmp_path / "mock_project_results.json", {"Cs": [[4.0]], "Ls": [[16.0]]})
    _write_json(tmp_path / "mock.json", {"parameters": {"width": 10}})

    _run_post_process_script(monkeypatch, tmp_path, "produce_z0_table.py")

    row = _read_single_row(tmp_path / f"{tmp_path.name}_Z0.csv")
    assert row == {
        "key": "mock",
        "Cs": "4.0",
        "Ls": "16.0",
        "Z0": "2.0",
        "c_eff": "0.125",
    }


def test_produce_epr_table_writes_energy_participation_csv(monkeypatch, tmp_path):
    _write_json(tmp_path / "mock_project_results.json", {"E_signal": [2.0], "E_ground": [6.0]})
    _write_json(
        tmp_path / "mock.json",
        {
            "name": "mock",
            "parameters": {"width": 10},
            "ports": [],
            "layers": {
                "signal": {"excitation": 1},
                "ground": {"excitation": 0},
            },
        },
    )

    _run_post_process_script(monkeypatch, tmp_path, "produce_epr_table.py")

    row = _read_single_row(tmp_path / f"{tmp_path.name}_epr.csv")
    assert row == {
        "key": "mock",
        "result_index": "1",
        "E_total": "8.0",
        "p_ground": "0.75",
        "p_signal": "0.25",
    }


def test_elmer_profiler_writes_profile_csv_from_mock_logs(monkeypatch, tmp_path):
    _write_json(
        tmp_path / "mock.json",
        {
            "parameters": {"width": 10},
            "mesh_name": "mock_mesh",
            "workflow": {"elmer_n_processes": 2, "elmer_n_threads": 3, "gmsh_n_threads": 4},
        },
    )
    _write_json(tmp_path / "mock_project_results.json", {})

    log_files = tmp_path / "log_files"
    log_files.mkdir()
    (log_files / "mock_mesh.Gmsh.log").write_text(
        "Info    : Done meshing 1D (Wall 0.2s, CPU 0.3s)\n"
        "Info    : Done meshing 2D (Wall 0.4s, CPU 0.5s)\n",
        encoding="utf-8",
    )
    (log_files / "mock.Elmer.log").write_text(
        "other line\nSOLVER TOTAL TIME(CPU,REAL): 1.5 2.5\n",
        encoding="utf-8",
    )
    mesh_dir = tmp_path / "mock_mesh"
    mesh_dir.mkdir()
    (mesh_dir / "mesh.header").write_text("header 321\n", encoding="utf-8")

    _run_post_process_script(monkeypatch, tmp_path, "elmer_profiler.py")

    row = _read_single_row(tmp_path / f"{tmp_path.name}_profile.csv")
    assert row == {
        "key": "mock",
        "elmer_elements": "321",
        "elmer_n_processes": "2",
        "elmer_n_threads": "3",
        "elmer_time_cpu": "3.0",
        "elmer_time_real": "2.5",
        "gmsh_n_threads": "4",
        "gmsh_time_cpu": "0.8",
        "gmsh_time_real": "0.6000000000000001",
    }


def test_elmer_cleanup_skips_non_simulation_directories(monkeypatch, tmp_path):
    calls = []
    fake_elmer_helpers = types.ModuleType("elmer_helpers")
    fake_elmer_helpers.delete_meshes = lambda path, simname: calls.append((Path(path), simname))
    monkeypatch.setitem(sys.modules, "elmer_helpers", fake_elmer_helpers)

    for folder in ("scripts", "log_files", "elmer_data", "s_matrix_plots", "mock_simulation"):
        (tmp_path / folder).mkdir()

    _run_post_process_script(monkeypatch, tmp_path, "elmer_cleanup.py")

    assert calls == [(tmp_path, "mock_simulation")]
