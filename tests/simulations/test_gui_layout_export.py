# This code is part of KQCircuits
# Copyright (C) 2025 IQM Finland Oy
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


def test_collect_ports_finds_launchers_and_qubit():
    layout, top = _design_with_two_launchers_and_qubit()
    ports, edge_directions = collect_ports(top)

    edge_ports = [p for p in ports if isinstance(p, EdgePort)]
    internal_ports = [p for p in ports if isinstance(p, InternalPort)]
    assert len(edge_ports) == 2
    assert len(internal_ports) == 1
    # Each EdgePort has a recorded outward direction, the InternalPort does not.
    assert set(edge_directions) == {p.number for p in edge_ports}
    # The qubit junction provides a ground location for its internal port.
    assert hasattr(internal_ports[0], "ground_location")
    assert layout.cells() > 0


def test_edge_ports_land_on_box_edges():
    layout, top = _design_with_two_launchers_and_qubit()
    ports, edge_directions = collect_ports(top)
    box = simulation_box(top, ports, edge_directions, margin=100.0)
    assert layout.cells() > 0

    for port in ports:
        direction = edge_directions.get(port.number)
        if direction is None:
            continue
        location = port.signal_location
        if abs(direction.x) >= abs(direction.y):
            edge = box.right if direction.x > 0 else box.left
            assert location.x == pytest.approx(edge, abs=1e-6)
        else:
            edge = box.top if direction.y > 0 else box.bottom
            assert location.y == pytest.approx(edge, abs=1e-6)


def test_simulation_box_projects_ports_onto_edges_including_zero():
    # A left edge at x=0 used to be dropped as a falsy value, and ports on one side that are slightly
    # misaligned must still end up on a single straight edge.
    layout = pya.Layout()
    top = layout.create_cell("Top")
    top.shapes(layout.layer(1, 0)).insert(pya.DBox(-500.0, -500.0, 500.0, 500.0))

    right_high = EdgePort(1, pya.DPoint(480.0, 100.0))
    right_low = EdgePort(2, pya.DPoint(495.0, -100.0))
    left_at_zero = EdgePort(3, pya.DPoint(0.0, 250.0))
    directions = {1: pya.DVector(1, 0), 2: pya.DVector(1, 0), 3: pya.DVector(-1, 0)}

    box = simulation_box(top, [right_high, right_low, left_at_zero], directions, margin=100.0)

    # The left edge follows the launcher at x=0, it does not fall back to the bounding box minus margin.
    assert box.left == pytest.approx(0.0)
    assert left_at_zero.signal_location.x == pytest.approx(0.0)
    # The right edge is the outermost right port, and both right ports are projected onto it.
    assert box.right == pytest.approx(495.0)
    assert right_high.signal_location.x == pytest.approx(495.0)
    assert right_low.signal_location.x == pytest.approx(495.0)


def test_layout_without_launchers_has_no_edge_ports():
    layout = pya.Layout()
    top = layout.create_cell("Top")
    qubit = Swissmon.create(layout)
    top.insert(pya.DCellInstArray(qubit.cell_index(), pya.DCplxTrans(1, 0, False, 0.0, 0.0)))

    _, edge_directions = collect_ports(top)
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
