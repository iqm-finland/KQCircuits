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

SCRIPT = "produce_epr_table.py"


def test_computes_energy_participation_ratios(write_simulation, run_post_process, read_csv):
    write_simulation(
        "waveguide",
        {"name": "waveguide", "layers": {"signal": {"excitation": 1}, "ground": {"excitation": 0}}},
        {"E_substrate": [2.0], "E_vacuum": [6.0]},
    )

    sim_folder = run_post_process(SCRIPT)

    rows = read_csv(sim_folder / f"{sim_folder.name}_epr.csv")
    assert len(rows) == 1
    row = rows[0]
    # EPR is the energy in a layer divided by the total energy, here 2 + 6 = 8
    assert float(row["E_total"]) == pytest.approx(8.0)
    assert float(row["p_substrate"]) == pytest.approx(2.0 / 8.0)
    assert float(row["p_vacuum"]) == pytest.approx(6.0 / 8.0)
