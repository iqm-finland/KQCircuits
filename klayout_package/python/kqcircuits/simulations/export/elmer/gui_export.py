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

"""Export a manually drawn KLayout layout as an Elmer simulation.

These helpers back the ``export_elmer.lym`` macro. They walk the element hierarchy of a top cell, place
simulation ports at launchers and qubit junctions, work out the simulation box from the launcher positions,
and hand the result to :func:`export_elmer`. The logic lives here, separate from the macro, so it can be
exercised without the KLayout GUI.

Elements are identified both from live PCell data (the usual case when a design is open in the GUI) and, as a
fallback, from the cell name when the layout has been flattened or loaded from a file without PCell context.
"""

import logging
import math
from itertools import count
from pathlib import Path
from typing import Optional

from kqcircuits.pya_resolver import pya
from kqcircuits.defaults import default_layers
from kqcircuits.elements.element import get_refpoints
from kqcircuits.elements.launcher import Launcher
from kqcircuits.qubits.qubit import Qubit
from kqcircuits.simulations.port import EdgePort, InternalPort
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.simulations.export.elmer.elmer_solution import ElmerVectorHelmholtzSolution
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.elmer.mesh_size_helpers import refine_metal_edges

__all__ = [
    "default_workflow",
    "default_mesh_size",
    "collect_ports",
    "simulation_box",
    "export_open_layout_to_elmer",
]


def default_workflow():
    """Return the default Elmer workflow used by the GUI export."""
    return {
        "run_gmsh_gui": True,
        "run_elmergrid": True,
        "run_elmer": True,
        "run_paraview": True,
        "python_executable": "python",
        "gmsh_n_threads": -1,
        "elmer_n_processes": -1,
        "elmer_n_threads": 1,
    }


def default_mesh_size():
    """Return the default mesh size dictionary, refined at the metal edges."""
    return {"global_max": 200.0, **refine_metal_edges(10, 1.0)}


def _class_name(cell):
    """Return the KQC element class name the cell was generated from.

    Cell names look like ``Launcher``, ``Swissmon$1`` or ``Double*Pads``, where ``$`` marks a variant and
    ``*`` stands for a space. This strips those so the result matches the element class display name.
    """
    return cell.name.split("$")[0].replace("*", " ").strip()


def _has_sim_junction(cell, layout):
    """Return True if the cell directly contains a Sim junction instance."""
    return any(_class_name(layout.cell(inst.cell_index)) == "Sim" for inst in cell.each_inst())


def _is_launcher(inst, cell):
    """Return True if the instance is a Launcher, from PCell data or the cell name."""
    pcell = inst.pcell_declaration()
    if pcell is not None:
        return isinstance(pcell, Launcher)
    return _class_name(cell) == "Launcher"


def _is_qubit(inst, cell, layout):
    """Return True if the instance is a qubit, from PCell data or a Sim junction child."""
    pcell = inst.pcell_declaration()
    if pcell is not None:
        return isinstance(pcell, Qubit)
    return _has_sim_junction(cell, layout)


def _outward_direction(trans):
    """Return the normalised global direction of the launcher local +x axis.

    The launcher pad and the chip edge sit on the local +x side, so this vector points outward from the
    design. It is taken from transformed points rather than the rotation code so it stays correct under
    mirroring. The result is always normalised to unit length so callers can rely on that contract even
    when the launcher was placed with a non-unit scale transform.
    """
    raw = (trans * pya.DPoint(1, 0)) - (trans * pya.DPoint(0, 0))
    length = raw.abs()
    return raw / length if length > 1e-12 else raw


def _launcher_signal_location(inst, cell, trans):
    """Return the EdgePort location at the launcher pad edge, in global coordinates.

    With PCell data the pad edge is at local ``(s + l, 0)``, the point opposite the launcher opening. For a
    flat cell the same edge is taken from the local bounding box along +x.

    Raises:
        ValueError: if the PCell parameters ``s`` or ``l`` exist but cannot be interpreted as numbers,
            which would indicate corrupted or unexpected parameter data.
    """
    params = inst.pcell_parameters_by_name()
    if "s" in params and "l" in params:
        try:
            reach = float(params["s"]) + float(params["l"])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Launcher PCell parameters 's' and 'l' must be numeric; "
                f"got s={params['s']!r}, l={params['l']!r}."
            ) from exc
    else:
        reach = cell.dbbox().right
    return trans * pya.DPoint(reach, 0)


def _squid_ports(
    cell, trans, refpoint_layer
) -> Optional[tuple[pya.DPoint, pya.DPoint]]:
    """Return the global (signal, ground) points of a qubit Sim junction, or None if absent.

    ``get_refpoints`` returns a plain ``dict``; no ``.dict()`` call is needed or valid.
    Iterating over ``.items()`` lets us reuse the already-resolved signal DPoint directly
    rather than performing a second dict lookup.
    """
    # get_refpoints returns a plain dict — do not call .dict() on it.
    refpoints = get_refpoints(refpoint_layer, cell, pya.DTrans(), None)
    for name, signal_pt in refpoints.items():
        if name.endswith("port_squid_a"):
            ground_name = name[:-1] + "b"
            if ground_name in refpoints:
                return trans * signal_pt, trans * refpoints[ground_name]
    return None


def collect_ports(top_cell) -> tuple[list, dict[int, pya.DVector]]:
    """Walk ``top_cell`` and build the simulation ports from launchers and qubits.

    Returns a tuple ``(ports, edge_directions)``. ``ports`` is the list of :class:`Port`.
    ``edge_directions`` maps each EdgePort number to its outward unit :class:`pya.DVector`, used to
    place that port on the box edge. Launchers and qubits are treated as leaves; every other instance
    is descended into so elements nested in sub-designs are still found.

    The instance list for each cell is snapshotted with ``list()`` before iteration for two reasons:

    1. Setting ``junction_type`` on a qubit regenerates its child cell, which would invalidate a live
       KLayout instance iterator.
    2. Any cell modification (including recursive ``visit`` calls) can invalidate live iterators in
       KLayout's C++ layer.

    A ``visited`` set tracks the current recursion stack so that genuine hierarchy cycles — where
    cell A contains cell B which contains cell A again — are detected and broken before the Python
    call stack overflows. This does **not** prevent the same cell definition from being visited
    multiple times via distinct hierarchy paths (e.g. two separate instances of the same cell placed
    at different locations), which is normal and correct KLayout usage. The ``visited`` set is a
    path-tracking guard, not a global deduplication set: a key is added on entry and removed only
    on exit so sibling instances share no state.

    Port numbers are generated with :func:`itertools.count` rather than a mutable list-cell so the
    intent is clear and the counter cannot accidentally be shared across calls.
    """
    layout = top_cell.layout()
    refpoint_layer = layout.layer(default_layers["refpoints"])
    ports: list = []
    edge_directions: dict[int, pya.DVector] = {}
    port_numbers = count(1)
    # Tracks the active recursion path to detect back-edges (cycles). NOT a global visit set.
    recursion_stack: set[int] = set()

    def visit(cell, trans: pya.DCplxTrans) -> None:
        key = cell.cell_index()
        if key in recursion_stack:
            logging.warning(
                "collect_ports: hierarchy cycle detected at cell '%s' (index %d); "
                "skipping this back-edge to prevent infinite recursion. "
                "Check the layout hierarchy for circular cell references.",
                cell.name,
                key,
            )
            return
        recursion_stack.add(key)

        # Snapshot instances before iterating — see docstring for why this is necessary.
        for inst in list(cell.each_inst()):
            child = layout.cell(inst.cell_index)
            child_trans = trans * inst.dcplx_trans
            if _is_launcher(inst, child):
                number = next(port_numbers)
                ports.append(EdgePort(number, _launcher_signal_location(inst, child, child_trans)))
                edge_directions[number] = _outward_direction(child_trans)
            elif _is_qubit(inst, child, layout):
                if inst.pcell_declaration() is not None:
                    # Only set junction_type if the parameter actually exists on this qubit.
                    # Checking first avoids a silent no-op or error on unexpected PCell schemas.
                    params = inst.pcell_parameters_by_name()
                    if "junction_type" in params:
                        inst["junction_type"] = "Sim"
                    child = layout.cell(inst.cell_index)
                squid = _squid_ports(child, child_trans, refpoint_layer)
                if squid is not None:
                    number = next(port_numbers)
                    ports.append(InternalPort(number, squid[0], squid[1]))
            else:
                visit(child, child_trans)

        # Pop this cell from the recursion stack on the way out so sibling branches can visit
        # other instances of the same cell definition without triggering the cycle guard.
        recursion_stack.discard(key)

    visit(top_cell, pya.DCplxTrans())
    return ports, edge_directions


def simulation_box(
    top_cell, ports: list, edge_directions: dict[int, pya.DVector], margin: float = 100.0
) -> pya.DBox:
    """Return the simulation box as a :class:`pya.DBox` and place the edge ports on its rim.

    The box starts from the cell bounding box grown by ``margin`` on every side. Each side that faces a
    launcher is then moved to the outermost EdgePort signal location on that side, overriding the
    margin-expanded default. Sides with no launcher keep the margin-expanded bounding box edge.

    Every EdgePort on a launcher side is then projected exactly onto that edge. Manual placement is rarely
    pixel perfect, so this projection guarantees each EdgePort sits on the box rim, which the Elmer export
    requires.

    Note on ``x=0`` and other falsy edge values: the original margin-expanded values are stored in a dict
    keyed by side name so that a launcher at ``x=0`` (a falsy float) correctly overrides the margin
    default rather than being silently skipped.

    Launcher-side classification:
        KLayout transforms place launchers at 0°, 90°, 180°, or 270°, producing exact axis-aligned
        direction vectors. The ``|dx| >= |dy|`` comparison therefore has a clear, unambiguous result
        in all normal cases. A tie at exactly 45° cannot arise with standard KLayout rotations, so no
        special epsilon handling is needed or added.

    A clear error is raised when the launcher orientations leave no room for a valid box — for example a
    port facing right that ends up left of the opposite side — or when any edge coordinate is not finite
    (NaN or infinity), which would indicate corrupted geometry coordinates.

    The ``signal_location`` of the affected EdgePorts is updated in place.
    """
    geometry = top_cell.dbbox()

    # Use a dict so that an edge value of 0.0 (falsy) is never confused with "no launcher on this side".
    edges: dict[str, float] = {
        "left": geometry.left - margin,
        "right": geometry.right + margin,
        "bottom": geometry.bottom - margin,
        "top": geometry.top + margin,
    }

    # Guard against NaN/Inf coordinates from corrupted geometry before doing any arithmetic.
    for side, value in edges.items():
        if not math.isfinite(value):
            raise ValueError(
                f"Simulation box edge '{side}' is not finite ({value}). "
                "Check the layout geometry for degenerate or corrupted shapes."
            )

    sides: dict[str, list] = {"left": [], "right": [], "bottom": [], "top": []}

    for port in ports:
        direction = edge_directions.get(port.number)
        if direction is None:
            continue
        if abs(direction.x) >= abs(direction.y):
            sides["right" if direction.x > 0 else "left"].append(port)
        else:
            sides["top" if direction.y > 0 else "bottom"].append(port)

    # Move each launcher-facing edge to the outermost port on that side.
    if sides["left"]:
        edges["left"] = min(port.signal_location.x for port in sides["left"])
    if sides["right"]:
        edges["right"] = max(port.signal_location.x for port in sides["right"])
    if sides["bottom"]:
        edges["bottom"] = min(port.signal_location.y for port in sides["bottom"])
    if sides["top"]:
        edges["top"] = max(port.signal_location.y for port in sides["top"])

    if edges["right"] - edges["left"] <= 0 or edges["top"] - edges["bottom"] <= 0:
        raise ValueError(
            "Could not define a simulation box from the launcher positions. Check that the launchers "
            "point outward and sit at the edge of the design."
        )

    # Project every EdgePort onto the final edge so it lands exactly on the rim.
    for port in sides["left"]:
        port.signal_location = pya.DPoint(edges["left"], port.signal_location.y)
    for port in sides["right"]:
        port.signal_location = pya.DPoint(edges["right"], port.signal_location.y)
    for port in sides["bottom"]:
        port.signal_location = pya.DPoint(port.signal_location.x, edges["bottom"])
    for port in sides["top"]:
        port.signal_location = pya.DPoint(port.signal_location.x, edges["top"])

    return pya.DBox(edges["left"], edges["bottom"], edges["right"], edges["top"])


def export_open_layout_to_elmer(
    top_cell, path, *, name="gui_simulation", target_frequency=5.0, mesh_size=None, workflow=None, margin=100.0
):
    """Export the geometry in ``top_cell`` as an Elmer wave equation simulation.

    Args:
        top_cell: the top cell whose geometry is exported. The cell is modified (qubit junctions are
            switched to Sim type and simulation layers are added), so the macro should pass a copy.
        path: directory the simulation files are written to.
        name: simulation name, also the file name stem.
        target_frequency: solver frequency in GHz.
        mesh_size: Gmsh mesh size dictionary, defaults to :func:`default_mesh_size`.
        workflow: Elmer workflow dictionary, defaults to :func:`default_workflow`.
        margin: distance in micrometers added around the geometry on sides without a launcher.

    Returns:
        Path to the written simulation directory (``path`` as a :class:`pathlib.Path`).

    Raises:
        ValueError: if no launchers are found in the layout or if the launcher positions cannot define
            a valid simulation box.
    """
    ports, edge_directions = collect_ports(top_cell)
    if not edge_directions:
        raise ValueError("No launchers found in the layout, cannot place edge ports for the simulation.")

    out_path = Path(path)
    out_path.mkdir(parents=True, exist_ok=True)

    box = simulation_box(top_cell, ports, edge_directions, margin)
    simulation = Simulation.from_cell(top_cell, name=name, box=box, ports=ports)
    solution = ElmerVectorHelmholtzSolution(
        mesh_size=default_mesh_size() if mesh_size is None else mesh_size,
        frequency=target_frequency,
        # Use first order basis since the model is very large.
        quadratic_approximation=False,
        linear_system_method="zmumps",
        use_multigrid_solver=False,
    )
    export_elmer([(simulation, solution)], out_path, workflow=default_workflow() if workflow is None else workflow)

    # Always return the output directory so callers can print or use the path reliably.
    # (export_elmer itself returns None in the current KQC implementation.)
    return out_path
