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

from post_process_test_helpers import read_csv, run_post_process, write_json


@pytest.mark.parametrize(
    ("cs", "ls", "expected_z0", "expected_c_eff"),
    [([[4.0]], [[9.0]], "1.5", "0.16666666666666666")],
)
def test_produce_z0_table_writes_impedance_and_effective_velocity(
    tmp_path, monkeypatch, cs, ls, expected_z0, expected_c_eff
):
    """`produce_z0_table.py` computes Z0 and c_eff from mocked C/L matrices."""
    write_json(tmp_path / "waveguide.json", {"parameters": {}})
    write_json(tmp_path / "waveguide_project_results.json", {"Cs": cs, "Ls": ls})

    run_post_process("produce_z0_table.py", tmp_path, monkeypatch, __file__)

    rows = read_csv(tmp_path / f"{tmp_path.name}_Z0.csv")
    assert rows == [
        {"key": "waveguide", "Cs": "4.0", "Ls": "9.0", "Z0": expected_z0, "c_eff": expected_c_eff}
    ]
