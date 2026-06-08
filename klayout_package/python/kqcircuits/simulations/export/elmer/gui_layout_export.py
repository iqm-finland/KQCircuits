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

from pathlib import Path

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
    """Return the global direction of the launcher local +x axis.

    The launcher pad and the chip edge sit on the local +x side, so this vector points outward from the
    design. It is taken from transformed points rather than the rotation code so it stays correct under
    mirroring.
    """
    return (trans * pya.DPoint(1, 0)) - (trans * pya.DPoint(0, 0))


def _launcher_signal_location(inst, cell, trans):
    """Return the EdgePort location at the launcher pad edge, in global coordinates.

    With PCell data the pad edge is at local ``(s + l, 0)``, the point opposite the launcher opening. For a
    flat cell the same edge is taken from the local bounding box along +x.
    """
    params = inst.pcell_parameters_by_name()
    if "s" in params and "l" in params:
        reach = params["s"] + params["l"]
    else:
        reach = cell.dbbox().right
    return trans * pya.DPoint(reach, 0)


def _squid_ports(cell, trans, refpoint_layer):
    """Return the global (signal, ground) points of a qubit Sim junction, or None if absent."""
    refpoints = get_refpoints(refpoint_layer, cell, pya.DTrans(), None).dict()
    for name in refpoints:
        if name.endswith("port_squid_a"):
            ground = name[:-1] + "b"
            if ground in refpoints:
                return trans * refpoints[name], trans * refpoints[ground]
    return None


def collect_ports(top_cell):
    """Walk ``top_cell`` and build the simulation ports from launchers and qubits.

    Returns a tuple ``(ports, edge_directions)``. ``ports`` is the list of :class:`Port`. ``edge_directions``
    maps each EdgePort number to its outward :class:`pya.DVector`, used to place that port on the box edge.
    Launchers and qubits are treated as leaves, every other instance is descended into so elements nested in
    sub designs are still found.
    """
    layout = top_cell.layout()
    refpoint_layer = layout.layer(default_layers["refpoints"])
    ports = []
    edge_directions = {}
    counter = [1]

    def visit(cell, trans):
        # Snapshot the instances first. Setting junction_type below regenerates a qubit cell, which would
        # invalidate a live instance iterator.
        for inst in list(cell.each_inst()):
            child = layout.cell(inst.cell_index)
            child_trans = trans * inst.dcplx_trans
            if _is_launcher(inst, child):
                ports.append(EdgePort(counter[0], _launcher_signal_location(inst, child, child_trans)))
                edge_directions[counter[0]] = _outward_direction(child_trans)
                counter[0] += 1
            elif _is_qubit(inst, child, layout):
                if inst.pcell_declaration() is not None:
                    inst["junction_type"] = "Sim"
                    child = layout.cell(inst.cell_index)
                squid = _squid_ports(child, child_trans, refpoint_layer)
                if squid is not None:
                    ports.append(InternalPort(counter[0], squid[0], squid[1]))
                    counter[0] += 1
            else:
                visit(child, child_trans)

    visit(top_cell, pya.DCplxTrans())
    return ports, edge_directions


def simulation_box(top_cell, ports, edge_directions, margin=100.0):
    """Return the simulation box as a :class:`pya.DBox` and place the edge ports on its rim.

    The box starts from the cell bounding box grown by ``margin``. Each side that faces a launcher is moved
    to the outermost EdgePort on that side, then every EdgePort on that side is projected exactly onto the
    edge. Manual placement is rarely pixel perfect, so this projection is what guarantees each EdgePort sits
    on the box rim, which the Elmer export requires. A clear error is raised when the launcher orientations
    leave no room for a valid box, for example a port facing right that ends up left of the opposite side.

    The ``signal_location`` of the affected EdgePorts is updated in place.
    """
    geometry = top_cell.dbbox()
    left, bottom = geometry.left - margin, geometry.bottom - margin
    right, top = geometry.right + margin, geometry.top + margin

    sides = {"left": [], "right": [], "bottom": [], "top": []}
    for port in ports:
        direction = edge_directions.get(port.number)
        if direction is None:
            continue
        if abs(direction.x) >= abs(direction.y):
            sides["right" if direction.x > 0 else "left"].append(port)
        else:
            sides["top" if direction.y > 0 else "bottom"].append(port)

    if sides["left"]:
        left = min(port.signal_location.x for port in sides["left"])
    if sides["right"]:
        right = max(port.signal_location.x for port in sides["right"])
    if sides["bottom"]:
        bottom = min(port.signal_location.y for port in sides["bottom"])
    if sides["top"]:
        top = max(port.signal_location.y for port in sides["top"])

    if right - left <= 0 or top - bottom <= 0:
        raise ValueError(
            "Could not define a simulation box from the launcher positions. Check that the launchers point "
            "outward and sit at the edge of the design."
        )

    for port in sides["left"]:
        port.signal_location = pya.DPoint(left, port.signal_location.y)
    for port in sides["right"]:
        port.signal_location = pya.DPoint(right, port.signal_location.y)
    for port in sides["bottom"]:
        port.signal_location = pya.DPoint(port.signal_location.x, bottom)
    for port in sides["top"]:
        port.signal_location = pya.DPoint(port.signal_location.x, top)

    return pya.DBox(left, bottom, right, top)


def export_open_layout_to_elmer(
    top_cell, path, *, name="gui_simulation", target_frequency=5.0, mesh_size=None, workflow=None, margin=100.0
):
    """Export the geometry in ``top_cell`` as an Elmer wave equation simulation.

    Args:
        top_cell: the top cell whose geometry is exported. The cell is modified, so the macro passes a copy.
        path: directory the simulation files are written to.
        name: simulation name, also the file name stem.
        target_frequency: solver frequency in GHz.
        mesh_size: Gmsh mesh size dictionary, defaults to :func:`default_mesh_size`.
        workflow: Elmer workflow dictionary, defaults to :func:`default_workflow`.
        margin: distance in micrometers added around the geometry on sides without a launcher.

    Returns:
        Path to the written simulation directory.
    """
    ports, edge_directions = collect_ports(top_cell)
    if not edge_directions:
        raise ValueError("No launchers found in the layout, cannot place edge ports for the simulation.")

    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    box = simulation_box(top_cell, ports, edge_directions, margin)
    simulation = Simulation.from_cell(top_cell, name=name, box=box, ports=ports)
    solution = ElmerVectorHelmholtzSolution(
        mesh_size=default_mesh_size() if mesh_size is None else mesh_size,
        frequency=target_frequency,
        # Use first order basis since the model is very large
        quadratic_approximation=False,
        linear_system_method="zmumps",
        use_multigrid_solver=False,
    )
    return export_elmer([(simulation, solution)], path, workflow=default_workflow() if workflow is None else workflow)
