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

from math import sqrt

import pytest

SCRIPT = "produce_z0_table.py"


def test_computes_impedance_and_effective_velocity(write_simulation, run_post_process, read_csv):
    cs, ls = 4.0, 9.0
    write_simulation("waveguide", {}, {"Cs": [[cs]], "Ls": [[ls]]})

    sim_folder = run_post_process(SCRIPT)

    rows = read_csv(sim_folder / f"{sim_folder.name}_Z0.csv")
    assert len(rows) == 1
    assert float(rows[0]["Cs"]) == pytest.approx(cs)
    assert float(rows[0]["Ls"]) == pytest.approx(ls)
    assert float(rows[0]["Z0"]) == pytest.approx(sqrt(ls / cs))
    assert float(rows[0]["c_eff"]) == pytest.approx(1.0 / sqrt(ls * cs))


def test_skips_results_without_cs_and_ls(write_simulation, run_post_process, read_csv):
    write_simulation("waveguide", {}, {"Cs": [[4.0]]})

    sim_folder = run_post_process(SCRIPT)

    assert read_csv(sim_folder / f"{sim_folder.name}_Z0.csv") == []
