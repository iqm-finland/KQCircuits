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
from pathlib import Path

import pytest


POST_PROCESS_DIR = Path("klayout_package/python/scripts/simulations/post_process")


def _write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def _run_post_process(script_name, tmp_path, monkeypatch):
    script_dir = Path(__file__).parents[3] / POST_PROCESS_DIR
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(script_dir))
    runpy.run_path(str(script_dir / script_name), run_name="__main__")


def _read_csv(path):
    with path.open(encoding="utf-8", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def test_produce_cmatrix_table_writes_capacitance_matrix_csv(tmp_path, monkeypatch):
    """`produce_cmatrix_table.py` turns mocked project capacitances into a result table."""
    _write_json(tmp_path / "waveguide.json", {"parameters": {}, "tool": "cross-section"})
    _write_json(tmp_path / "waveguide_project_results.json", {"CMatrix": [[1.0, 2.0], [3.0, 4.0]]})

    _run_post_process("produce_cmatrix_table.py", tmp_path, monkeypatch)

    rows = _read_csv(tmp_path / f"{tmp_path.name}_results.csv")
    assert rows == [{"key": "waveguide", "C11": "1.0", "C12": "2.0", "C21": "3.0", "C22": "4.0"}]


@pytest.mark.parametrize(
    ("cs", "ls", "expected_z0", "expected_c_eff"),
    [([[4.0]], [[9.0]], "1.5", "0.16666666666666666")],
)
def test_produce_z0_table_writes_impedance_and_effective_velocity(
    tmp_path, monkeypatch, cs, ls, expected_z0, expected_c_eff
):
    """`produce_z0_table.py` computes Z0 and c_eff from mocked C/L matrices."""
    _write_json(tmp_path / "waveguide.json", {"parameters": {}})
    _write_json(tmp_path / "waveguide_project_results.json", {"Cs": cs, "Ls": ls})

    _run_post_process("produce_z0_table.py", tmp_path, monkeypatch)

    rows = _read_csv(tmp_path / f"{tmp_path.name}_Z0.csv")
    assert rows == [
        {"key": "waveguide", "Cs": "4.0", "Ls": "9.0", "Z0": expected_z0, "c_eff": expected_c_eff}
    ]


def test_elmer_profiler_collects_runtime_and_mesh_statistics(tmp_path, monkeypatch):
    """`elmer_profiler.py` compiles mocked Gmsh, Elmer, workflow, and mesh data into a profile table."""
    _write_json(
        tmp_path / "waveguide.json",
        {
            "parameters": {},
            "mesh_name": "waveguide_mesh",
            "workflow": {"elmer_n_processes": 2, "elmer_n_threads": 3, "gmsh_n_threads": 4},
        },
    )
    _write_json(tmp_path / "waveguide_project_results.json", {})

    log_dir = tmp_path / "log_files"
    log_dir.mkdir()
    (log_dir / "waveguide_mesh.Gmsh.log").write_text(
        "\n".join(
            [
                "Info    : Done meshing 1D (Wall 0.10s, CPU 0.20s)",
                "Info    : Done meshing 2D (Wall 0.30s, CPU 0.40s)",
            ]
        ),
        encoding="utf-8",
    )
    (log_dir / "waveguide.Elmer.log").write_text(
        "SOLVER TOTAL TIME(CPU,REAL): 5.0 7.5\n",
        encoding="utf-8",
    )
    mesh_dir = tmp_path / "waveguide_mesh"
    mesh_dir.mkdir()
    (mesh_dir / "mesh.header").write_text("header 123 other data\n", encoding="utf-8")

    _run_post_process("elmer_profiler.py", tmp_path, monkeypatch)

    rows = _read_csv(tmp_path / f"{tmp_path.name}_profile.csv")
    assert rows == [
        {
            "key": "waveguide",
            "elmer_elements": "123",
            "elmer_n_processes": "2",
            "elmer_n_threads": "3",
            "elmer_time_cpu": "10.0",
            "elmer_time_real": "7.5",
            "gmsh_n_threads": "4",
            "gmsh_time_cpu": "0.6000000000000001",
            "gmsh_time_real": "0.4",
        }
    ]
