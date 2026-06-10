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

import json

import pandas as pd
import pytest


def test_computes_quality_factors_from_epr_table(write_simulation, run_post_process, sim_folder):
    # `produce_q_factor_table.py` consumes the table written by `produce_epr_table.py`, so run that first
    write_simulation(
        "waveguide",
        {"name": "waveguide", "layers": {"signal": {"excitation": 1}, "ground": {"excitation": 0}}},
        {"E_substrate": [2.0], "E_vacuum": [6.0]},
    )
    run_post_process("produce_epr_table.py")

    loss_tangents = {"substrate": 0.001, "vacuum": 0.002}
    (sim_folder / "loss_tangents.json").write_text(json.dumps(loss_tangents), encoding="utf-8")
    run_post_process("produce_q_factor_table.py", args=["loss_tangents.json"])

    row = pd.read_csv(sim_folder / f"{sim_folder.name}_q_factors.csv").iloc[0]
    p_substrate, p_vacuum = 2.0 / 8.0, 6.0 / 8.0
    assert row["Q_substrate"] == pytest.approx(1.0 / (p_substrate * loss_tangents["substrate"]))
    assert row["Q_vacuum"] == pytest.approx(1.0 / (p_vacuum * loss_tangents["vacuum"]))
    assert row["Q_total"] == pytest.approx(
        1.0 / (p_substrate * loss_tangents["substrate"] + p_vacuum * loss_tangents["vacuum"])
    )
