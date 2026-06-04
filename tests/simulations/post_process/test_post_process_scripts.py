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

import pytest


def test_produce_cmatrix_table_writes_capacitance_matrix(post_process_sandbox):
    post_process_sandbox.write_json(
        "sample.json",
        {
            "parameters": {"width": 10},
            "ports": [],
            "tool": "capacitance",
        },
    )
    post_process_sandbox.write_json("sample_project_results.json", {"Cs": [[1.0, 0.2], [0.2, 1.5]]})

    post_process_sandbox.run_script("produce_cmatrix_table.py")

    rows = post_process_sandbox.csv_rows("_results.csv")
    assert rows == [
        {
            "key": "sample",
            "C11": "1.0",
            "C12": "0.2",
            "C21": "0.2",
            "C22": "1.5",
        }
    ]


def test_produce_z0_table_writes_waveguide_parameters(post_process_sandbox):
    post_process_sandbox.write_json("line.json", {"parameters": {"width": 10}})
    post_process_sandbox.write_json("line_project_results.json", {"Cs": [[4.0]], "Ls": [[9.0]]})

    post_process_sandbox.run_script("produce_z0_table.py")

    row = post_process_sandbox.csv_rows("_Z0.csv")[0]
    assert row["key"] == "line"
    assert float(row["Cs"]) == 4.0
    assert float(row["Ls"]) == 9.0
    assert float(row["Z0"]) == 1.5
    assert float(row["c_eff"]) == pytest.approx(1 / 6)


def test_elmer_profiler_writes_runtime_and_mesh_statistics(post_process_sandbox):
    post_process_sandbox.write_json(
        "profiled.json",
        {
            "parameters": {"width": 10},
            "mesh_name": "profiled_mesh",
            "workflow": {
                "elmer_n_processes": 2,
                "elmer_n_threads": 3,
                "gmsh_n_threads": 4,
            },
        },
    )
    post_process_sandbox.write_json("profiled_project_results.json", {})
    post_process_sandbox.write_text(
        "log_files/profiled.Elmer.log",
        "noise\nSOLVER TOTAL TIME(CPU,REAL): 5.00 7.50\n",
    )
    post_process_sandbox.write_text(
        "log_files/profiled_mesh.Gmsh.log",
        "Info    : Done meshing 1D (Wall 0.25s, CPU 0.50s)\n"
        "Info    : Done meshing 2D (Wall 1.25s, CPU 1.50s)\n",
    )
    post_process_sandbox.write_text("profiled_mesh/mesh.header", "4 123 0\n")

    post_process_sandbox.run_script("elmer_profiler.py")

    row = post_process_sandbox.csv_rows("_profile.csv")[0]
    assert row["key"] == "profiled"
    assert row["elmer_n_processes"] == "2"
    assert row["elmer_n_threads"] == "3"
    assert row["gmsh_n_threads"] == "4"
    assert row["elmer_elements"] == "123"
    assert float(row["elmer_time_cpu"]) == 10.0
    assert float(row["elmer_time_real"]) == 7.5
    assert float(row["gmsh_time_cpu"]) == 2.0
    assert float(row["gmsh_time_real"]) == 1.5


def test_produce_q_factor_table_writes_q_values_from_existing_epr(post_process_sandbox):
    post_process_sandbox.write_json("sample.json", {"parameters": {"width": 10}})
    post_process_sandbox.write_json("sample_project_results.json", {})
    loss_tangents = post_process_sandbox.write_json("loss_tangents.json", {"ma": 0.001, "ms": 0.002})
    post_process_sandbox.write_text("sample_epr.csv", "key,E_total,p_ma,p_ms\nsample,1.0,0.25,0.5\n")

    post_process_sandbox.run_script("produce_q_factor_table.py", loss_tangents)

    row = post_process_sandbox.csv_rows("_q_factors.csv")[0]
    assert row["key"] == "sample"
    assert float(row["Q_ma"]) == 4000.0
    assert float(row["Q_ms"]) == 1000.0
    assert float(row["Q_total"]) == 800.0
