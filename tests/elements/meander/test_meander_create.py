# This code is part of KQCircuits
# Copyright (C) 2021 IQM Finland Oy
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


from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import get_cell_path_length

from kqcircuits.elements.meander import Meander
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.defaults import default_layers, default_airbridge_type


relative_length_tolerance = 1e-3
continuity_tolerance = 0.0015


def test_length_short_meander_r50():
    relative_error = _get_meander_length_error(1200, 4, 500, 50)
    assert relative_error < relative_length_tolerance


def test_length_long_meander_r50():
    relative_error = _get_meander_length_error(10000, 16, 2000, 50)
    assert relative_error < relative_length_tolerance


def test_length_long_meander_r25():
    relative_error = _get_meander_length_error(10000, 32, 2000, 25)
    assert relative_error < relative_length_tolerance


def test_length_long_meander_r100():
    relative_error = _get_meander_length_error(10000, 8, 2000, 100)
    assert relative_error < relative_length_tolerance


def test_length_min_num_meanders_r25():
    relative_error = _get_meander_length_error(1000, 2, 500, 25)
    assert relative_error < relative_length_tolerance


def test_length_min_num_meanders_r100():
    relative_error = _get_meander_length_error(1400, 2, 700, 100)
    assert relative_error < relative_length_tolerance


def test_length_non_90_deg_turns():
    relative_error = _get_meander_length_error(5200, -1, 2720, 100)
    assert relative_error < relative_length_tolerance


def test_length_close_to_90_deg_turns():
    relative_error = _get_meander_length_error(4725.9, -1, 2000, 100)
    assert relative_error < relative_length_tolerance


def test_continuity_short_meander():
    layout = pya.Layout()
    meander_cell = Meander.create(layout, start=pya.DPoint(0, 0), end=pya.DPoint(800, 0), length=1600, meanders=4, r=50)
    assert WaveguideCoplanar.is_continuous(
        meander_cell, layout.layer(default_layers["1t1_waveguide_path"]), continuity_tolerance
    )


def test_continuity_long_meander():
    layout = pya.Layout()
    meander_cell = Meander.create(
        layout, start=pya.DPoint(0, 0), end=pya.DPoint(2500, 0), length=9000, meanders=15, r=50
    )
    assert WaveguideCoplanar.is_continuous(
        meander_cell, layout.layer(default_layers["1t1_waveguide_path"]), continuity_tolerance
    )


def test_bridges_horizontal_meander():
    layout = pya.Layout()
    meander_cell = Meander.create(layout, start=pya.DPoint(0, 0), end=pya.DPoint(1000, 0), length=3000, n_bridges=5)
    bridge_positions = [
        pya.DPoint(273.244, 271.733),
        pya.DPoint(301.582, -221.366),
        pya.DPoint(500, 0),
        pya.DPoint(698.418, 221.366),
        pya.DPoint(726.756, -271.733),
    ]
    assert _bridges_at_correct_positions(layout, meander_cell, bridge_positions)


def test_bridges_vertical_meander():
    layout = pya.Layout()
    meander_cell = Meander.create(
        layout, start=pya.DPoint(0, 0), end=pya.DPoint(0, -1500), length=4000, meanders=4, n_bridges=5
    )
    bridge_positions = [
        pya.DPoint(346.573, -390.567),
        pya.DPoint(-179.794, -550),
        pya.DPoint(0, -750),
        pya.DPoint(179.794, -950),
        pya.DPoint(-346.573, -1109.433),
    ]
    assert _bridges_at_correct_positions(layout, meander_cell, bridge_positions)


def test_bridges_non_90_deg_turns():
    layout = pya.Layout()
    meander_cell = Meander.create(layout, start=pya.DPoint(0, 0), end=pya.DPoint(1200, 0), length=1500, n_bridges=6)
    bridge_positions = [
        pya.DPoint(198.351, 75.475),
        pya.DPoint(348.247, -61.056),
        pya.DPoint(512.211, 23.376),
        pya.DPoint(687.789, 23.376),
        pya.DPoint(851.753, -61.056),
        pya.DPoint(1001.649, 75.475),
    ]
    assert _bridges_at_correct_positions(layout, meander_cell, bridge_positions)


def _get_meander_length_error(meander_length, num_meanders, end, r):
    """Returns the relative error of the meander length for a meander with the given parameters."""
    layout = pya.Layout()
    meander_cell = Meander.create(
        layout, start=pya.DPoint(0, 0), end=pya.DPoint(end, 0), length=meander_length, meanders=num_meanders, r=r
    )
    true_length = get_cell_path_length(meander_cell)
    relative_error = abs(true_length - meander_length) / meander_length
    return relative_error


def _bridges_at_correct_positions(layout, meander_cell, bridge_positions):
    for inst in meander_cell.each_inst():
        # workaround for getting the cell due to KLayout bug, see
        # https://www.klayout.de/forum/discussion/1191/cell-shapes-cannot-call-non-const-method-on-a-const-reference
        # TODO: replace by `inst_cell = inst.cell` once KLayout bug is fixed
        inst_cell = layout.cell(inst.cell_index)
        if inst_cell.name == default_airbridge_type:
            correct_position = False
            for bridge_pos in bridge_positions:
                if (inst.dtrans.disp - bridge_pos).length() < 1e-3:
                    correct_position = True
                    break
            if not correct_position:
                return False
    return True
