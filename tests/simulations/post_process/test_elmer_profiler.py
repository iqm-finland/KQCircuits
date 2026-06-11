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

from post_process_test_helpers import read_csv, run_post_process, write_json


def test_elmer_profiler_collects_runtime_and_mesh_statistics(tmp_path, monkeypatch):
    """`elmer_profiler.py` compiles mocked runtime and mesh data into a profile table."""
    write_json(
        tmp_path / "waveguide.json",
        {
            "parameters": {},
            "mesh_name": "waveguide_mesh",
            "workflow": {"elmer_n_processes": 2, "elmer_n_threads": 3, "gmsh_n_threads": 4},
        },
    )
    write_json(tmp_path / "waveguide_project_results.json", {})

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

    run_post_process("elmer_profiler.py", tmp_path, monkeypatch, __file__)

    rows = read_csv(tmp_path / f"{tmp_path.name}_profile.csv")
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
