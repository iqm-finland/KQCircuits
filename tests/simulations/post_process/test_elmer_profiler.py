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

SCRIPT = "elmer_profiler.py"


@pytest.fixture
def profiled_simulation(write_simulation, sim_folder):
    """Set up the log files and mesh header that `elmer_profiler.py` reads for a single simulation."""
    mesh_name = "waveguide_mesh"
    write_simulation(
        "waveguide",
        {
            "mesh_name": mesh_name,
            "workflow": {"elmer_n_processes": 2, "elmer_n_threads": 3, "gmsh_n_threads": 4},
        },
        {},
    )

    log_files = sim_folder / "log_files"
    log_files.mkdir()
    gmsh_log = "\n".join(
        [
            "Info    : Done meshing 1D (Wall 0.10s, CPU 0.20s)",
            "Info    : Done meshing 2D (Wall 0.30s, CPU 0.40s)",
        ]
    )
    (log_files / f"{mesh_name}.Gmsh.log").write_text(gmsh_log + "\n", encoding="utf-8")
    (log_files / "waveguide.Elmer.log").write_text("SOLVER TOTAL TIME(CPU,REAL): 5.0 7.5\n", encoding="utf-8")

    mesh_dir = sim_folder / mesh_name
    mesh_dir.mkdir()
    (mesh_dir / "mesh.header").write_text("header 123 other\n", encoding="utf-8")
    return sim_folder


def test_collects_runtimes_and_mesh_size(profiled_simulation, run_post_process, read_csv):
    sim_folder = profiled_simulation
    run_post_process(SCRIPT)

    rows = read_csv(sim_folder / f"{sim_folder.name}_profile.csv")
    assert len(rows) == 1
    row = rows[0]
    assert row["elmer_elements"] == "123"
    assert float(row["gmsh_time_real"]) == pytest.approx(0.10 + 0.30)
    assert float(row["gmsh_time_cpu"]) == pytest.approx(0.20 + 0.40)
    assert float(row["elmer_time_real"]) == pytest.approx(7.5)
    # CPU time is scaled by the number of Elmer processes
    assert float(row["elmer_time_cpu"]) == pytest.approx(2 * 5.0)
