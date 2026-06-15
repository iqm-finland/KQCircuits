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

SCRIPT = "produce_cmatrix_table.py"


def results_csv(sim_folder):
    return sim_folder / f"{sim_folder.name}_results.csv"


def test_flattens_capacitance_matrix(write_simulation, run_post_process, read_csv):
    write_simulation("waveguide", {"tool": "cross-section"}, {"CMatrix": [[1.0, 2.0], [3.0, 4.0]]})

    sim_folder = run_post_process(SCRIPT)

    rows = read_csv(results_csv(sim_folder))
    assert len(rows) == 1
    assert rows[0]["key"] == "waveguide"
    assert [float(rows[0][f"C{i}{j}"]) for i in (1, 2) for j in (1, 2)] == [1.0, 2.0, 3.0, 4.0]


def test_falls_back_to_cs_field(write_simulation, run_post_process, read_csv):
    write_simulation("waveguide", {"tool": "cross-section"}, {"Cs": [[5.0]]})

    sim_folder = run_post_process(SCRIPT)

    rows = read_csv(results_csv(sim_folder))
    assert float(rows[0]["C11"]) == 5.0


def test_deembeds_capacitance_from_cross_section(write_simulation, run_post_process, read_csv):
    # 3D simulation with a port that should be deembedded using a separate cross-section simulation
    write_simulation(
        "sim",
        {
            "tool": "capacitance",
            "name": "sim",
            "ports": [{"deembed_len": 100, "deembed_cross_section": "cs"}],
        },
        {"CMatrix": [[10.0, 1.0], [1.0, 10.0]]},
    )
    write_simulation(
        "sim_cs",
        {"tool": "cross-section", "layers": {"signal": {"excitation": 1}}},
        {"CMatrix": [[5.0]]},
    )

    sim_folder = run_post_process(SCRIPT)

    rows = {row["key"]: row for row in read_csv(results_csv(sim_folder))}
    deembed_c = 1e-6 * 100 * 5.0
    assert float(rows["sim"]["C11_deembed"]) == pytest.approx(deembed_c)
    assert float(rows["sim"]["C11"]) == pytest.approx(10.0 - deembed_c)
