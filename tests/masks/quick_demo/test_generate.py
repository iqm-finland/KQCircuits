# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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

import os

import pytest

from kqcircuits.pya_resolver import lay
from kqcircuits import defaults


@pytest.mark.slow
def test_generate_quick_demo(tmp_path):
    if not hasattr(lay, "LayoutView"):
        pytest.xfail("Stand-alone mask not supported on klayout < 0.28")

    _run_mask("masks/quick_demo.py", tmp_path)

    mask_path = tmp_path.joinpath("Quick_v1/Quick_v1-1t1")
    chips_path = tmp_path.joinpath("Quick_v1/Chips")

    assert chips_path.joinpath("DE1").exists()
    assert chips_path.joinpath("DE1/DE1.png").exists()
    assert chips_path.joinpath("DE1/DE1.oas").exists()
    assert chips_path.joinpath("CH1").exists()
    assert chips_path.joinpath("CH1/CH1.png").exists()
    assert chips_path.joinpath("CH1/CH1.oas").exists()
    assert mask_path.joinpath("Quick_v1-1t1.oas").exists()
    assert mask_path.joinpath("Quick_v1-1t1.png").exists()


def _run_mask(path, tmp_path):
    _locals = locals()
    file = os.path.join(defaults.SCRIPTS_PATH, path)
    with open(file, "r") as fp:
        code = fp.read()

    code = code.replace("MaskSet(name=", "MaskSet(export_path=tmp_path, name=")

    exec(code, globals(), _locals)  # pylint: disable=exec-used
