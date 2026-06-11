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

import pytest

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.launcher import Launcher
from kqcircuits.qubits.swissmon import Swissmon
from kqcircuits.simulations.port import EdgePort, InternalPort
from kqcircuits.simulations.export.elmer.gui_layout_export import (
    collect_ports,
    simulation_box,
    export_open_layout_to_elmer,
)


def _design_with_two_launchers_and_qubit():
    """Build a small layout with two launchers facing left and right and one qubit in the middle.

    Returns the layout and its top cell. The caller keeps a reference to the layout so it is not destroyed.
    """
    layout = pya.Layout()
    top = layout.create_cell("Top")
    west = Launcher.create(layout, s=300, l=300)
    top.insert(pya.DCellInstArray(west.cell_index(), pya.DCplxTrans(1, 180, False, 500.0, 1500.0)))
    east = Launcher.create(layout, s=300, l=300)
    top.insert(pya.DCellInstArray(east.cell_index(), pya.DCplxTrans(1, 0, False, 2500.0, 1500.0)))
    qubit = Swissmon.create(layout)
    top.insert(pya.DCellInstArray(qubit.cell_index(), pya.DCplxTrans(1, 0, False, 1500.0, 1500.0)))
    return layout, top


def _cell_with_bbox(left, bottom, right, top_):
    """Return a layout and a top cell whose bounding box is the given rectangle."""
    layout = pya.Layout()
    top = layout.create_cell("Top")
    top.shapes(layout.layer(1, 0)).insert(pya.DBox(left, bottom, right, top_))
    return layout, top


def test_collect_ports_finds_launchers_and_qubit():
    """collect_ports returns the launchers, the qubit port, their directions and footprints."""
    layout, top = _design_with_two_launchers_and_qubit()
    ports, edge_directions, edge_footprints = collect_ports(top)

    edge_ports = [p for p in ports if isinstance(p, EdgePort)]
    internal_ports = [p for p in ports if isinstance(p, InternalPort)]
    assert len(edge_ports) == 2
    assert len(internal_ports) == 1
    # Each EdgePort has a recorded outward direction and a footprint, the InternalPort does not.
    assert set(edge_directions) == {p.number for p in edge_ports}
    assert set(edge_footprints) == {p.number for p in edge_ports}
    assert all(isinstance(box, pya.DBox) for box in edge_footprints.values())
    # The qubit junction provides a ground location for its internal port.
    assert hasattr(internal_ports[0], "ground_location")
    assert layout.cells() > 0


def test_edge_ports_land_on_box_edges():
    """The two launcher signals land on the box rims and the qubit signal stays in the middle."""
    layout, top = _design_with_two_launchers_and_qubit()
    ports, edge_directions, edge_footprints = collect_ports(top)
    box = simulation_box(top, ports, edge_directions, edge_footprints, margin=100.0)
    assert layout.cells() > 0

    qubit_x = next(p.signal_location.x for p in ports if p.number not in edge_directions)
    # One signal on the left rim, one on the right rim, the qubit port in the middle.
    assert {p.signal_location.x for p in ports} == {box.left, box.right, qubit_x}


def test_simulation_box_follows_inner_launcher_and_keeps_outer_on_rim():
    """Use case 1: with a slight shift the box edge follows the launcher nearer the centre.

    The outer launcher is left partially outside the box, but the rim still crosses its footprint so it
    keeps a point on the box. A left launcher placed at x=0 also checks that a zero edge is not dropped.
    """
    layout, top = _cell_with_bbox(-1000.0, -1000.0, 1000.0, 1000.0)
    assert layout.cells() > 0

    inner_right = EdgePort(1, pya.DPoint(1000.0, 200.0))
    outer_right = EdgePort(2, pya.DPoint(1100.0, -200.0))
    left_at_zero = EdgePort(3, pya.DPoint(0.0, 250.0))
    directions = {1: pya.DVector(1, 0), 2: pya.DVector(1, 0), 3: pya.DVector(-1, 0)}
    footprints = {
        1: pya.DBox(700.0, 100.0, 1050.0, 300.0),
        2: pya.DBox(950.0, -300.0, 1150.0, -100.0),  # reaches back across x=1000
        3: pya.DBox(-50.0, 150.0, 200.0, 350.0),  # crosses x=0
    }

    box = simulation_box(top, [inner_right, outer_right, left_at_zero], directions, footprints, margin=100.0)

    # The right edge follows the inner launcher, not the outer one, and the left edge keeps the x=0 launcher.
    assert box.right == pytest.approx(1000.0)
    assert box.left == pytest.approx(0.0)
    # Both right ports are projected onto the inner edge, the left port onto x=0.
    assert inner_right.signal_location.x == pytest.approx(1000.0)
    assert outer_right.signal_location.x == pytest.approx(1000.0)
    assert left_at_zero.signal_location.x == pytest.approx(0.0)


def test_simulation_box_raises_when_launcher_too_far_out():
    """Use case 2: a launcher so far out that the rim cannot cross its footprint is rejected."""
    layout, top = _cell_with_bbox(-1000.0, -1000.0, 1000.0, 1000.0)
    assert layout.cells() > 0

    inner_right = EdgePort(1, pya.DPoint(1000.0, 200.0))
    far_right = EdgePort(2, pya.DPoint(1600.0, -200.0))
    directions = {1: pya.DVector(1, 0), 2: pya.DVector(1, 0)}
    footprints = {
        1: pya.DBox(700.0, 100.0, 1050.0, 300.0),
        2: pya.DBox(1450.0, -300.0, 1650.0, -100.0),  # does not reach back to x=1000
    }

    with pytest.raises(ValueError):
        simulation_box(top, [inner_right, far_right], directions, footprints, margin=100.0)


def test_layout_without_launchers_has_no_edge_ports():
    """A layout with only a qubit yields no edge ports or directions."""
    layout = pya.Layout()
    top = layout.create_cell("Top")
    qubit = Swissmon.create(layout)
    top.insert(pya.DCellInstArray(qubit.cell_index(), pya.DCplxTrans(1, 0, False, 0.0, 0.0)))

    _, edge_directions, _ = collect_ports(top)
    assert not edge_directions


def test_export_on_copied_layout_keeps_qubit_internal_port(tmp_path):
    # The macro copies the active layout into a new view before exporting, so the qubit must still be found
    # and switched to a Sim junction on the copy. A qubit drawn with the default Manhattan junction has no
    # squid ports, so the export has to convert it. Layout.assign keeps the PCell data that this relies on.
    layout, top = _design_with_two_launchers_and_qubit()
    copy_layout = pya.Layout()
    copy_layout.assign(layout)
    copy_top = [cell for cell in copy_layout.top_cells() if cell.name == top.name][0]

    no_run = {"run_gmsh_gui": False, "run_elmergrid": False, "run_elmer": False, "run_paraview": False}
    out_dir = tmp_path / "sim"
    export_open_layout_to_elmer(copy_top, out_dir, name="sim", workflow=no_run)

    data = json.loads((out_dir / "sim.json").read_text())
    edge = [p for p in data["ports"] if p["type"] == "EdgePort"]
    internal = [p for p in data["ports"] if p["type"] == "InternalPort"]
    assert len(edge) == 2
    assert len(internal) == 1
    assert (out_dir / "sim.gds").exists()


def test_export_raises_when_folder_exists(tmp_path):
    """The library refuses to overwrite an existing output folder."""
    layout, top = _design_with_two_launchers_and_qubit()
    copy_layout = pya.Layout()
    copy_layout.assign(layout)
    copy_top = [cell for cell in copy_layout.top_cells() if cell.name == top.name][0]

    out_dir = tmp_path / "sim"
    out_dir.mkdir()
    with pytest.raises(FileExistsError):
        export_open_layout_to_elmer(copy_top, out_dir, name="sim")
