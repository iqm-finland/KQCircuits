"""
KLayout macro for exporting the active GUI layout into an
Elmer wave-equation simulation.

This implementation is intended as a temporary / draft PR
submission that demonstrates:

1. Hierarchy scraping for launchers and qubits
2. Automatic simulation box generation
3. Automatic EdgePort and InternalPort generation
4. Exporting simulation files using export_elmer
5. Opening simulation preview in a separate KLayout tab

The implementation is intentionally conservative and focuses
on readability and maintainability.

PEP 8 compliant docstrings and comments are used throughout.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from kqcircuits.pya_resolver import pya
from kqcircuits.klayout_view import KLayoutView

from kqcircuits.defaults import default_layers
from kqcircuits.elements.launcher import Launcher
from kqcircuits.qubits.qubit import Qubit

from kqcircuits.simulations.simulation import Simulation
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer

from kqcircuits.simulations.port import EdgePort
from kqcircuits.simulations.port import InternalPort

from kqcircuits.simulations.export.elmer.elmer_solution import (
    ElmerVectorHelmholtzSolution,
)

from kqcircuits.simulations.export.util import refine_metal_edges

from kqcircuits.util.refpoints import get_refpoints


EXPORT_NAME = "gui_export_elmer"

EXPORT_DIR = (
    Path.home()
    / "KQCircuits"
    / "tmp"
    / EXPORT_NAME
)

MARGIN = 100.0


mesh_size = {
    "global_max": 200.0,
    **refine_metal_edges(10, 1.0),
}

solution = ElmerVectorHelmholtzSolution(
    mesh_size=mesh_size,
    frequency=5.0,
    quadratic_approximation=False,
    linear_system_method="zmumps",
    use_multigrid_solver=False,
)

workflow = {
    "run_gmsh_gui": True,
    "run_elmergrid": True,
    "run_elmer": True,
    "run_paraview": True,
    "python_executable": "python",
    "gmsh_n_threads": -1,
    "elmer_n_processes": -1,
    "elmer_n_threads": 1,
}


class HierarchyInstance:
    """Container for instance hierarchy traversal."""

    def __init__(
        self,
        instance: pya.Instance,
        transform: pya.DCplxTrans,
    ) -> None:
        self.instance = instance
        self.transform = transform


def iter_instances(
    layout: pya.Layout,
    cell: pya.Cell,
    parent_transform: pya.DCplxTrans | None = None,
) -> Iterable[HierarchyInstance]:
    """
    Recursively iterate over all instances in the hierarchy.

    Parameters
    ----------
    layout:
        Active layout object.

    cell:
        Cell to traverse.

    parent_transform:
        Accumulated hierarchy transform.
    """

    if parent_transform is None:
        parent_transform = pya.DCplxTrans()

    for inst in cell.each_inst():
        transform = parent_transform * inst.dcplx_trans

        yield HierarchyInstance(inst, transform)

        child_cell = layout.cell(inst.cell_index)

        yield from iter_instances(
            layout,
            child_cell,
            transform,
        )


def get_instance_refpoints(
    layout: pya.Layout,
    cell: pya.Cell,
) -> dict:
    """
    Return refpoints for a cell.

    Parameters
    ----------
    layout:
        Layout object.

    cell:
        Cell from which to extract refpoints.
    """

    ref_layer = layout.layer(
        default_layers["refpoints"]
    )

    return get_refpoints(ref_layer, cell)


def create_edge_port(
    number: int,
    launcher_position: pya.DPoint,
    direction: str,
    box: pya.DBox,
) -> EdgePort:
    """
    Create an EdgePort aligned to the simulation box edge.

    Parameters
    ----------
    number:
        Port number.

    launcher_position:
        Launcher position.

    direction:
        Launcher orientation.

    box:
        Simulation bounding box.
    """

    x = launcher_position.x
    y = launcher_position.y

    if direction == "west":
        signal_location = pya.DPoint(box.left, y)

    elif direction == "east":
        signal_location = pya.DPoint(box.right, y)

    elif direction == "north":
        signal_location = pya.DPoint(x, box.top)

    else:
        signal_location = pya.DPoint(x, box.bottom)

    return EdgePort(
        number=number,
        signal_location=signal_location,
    )


def determine_launcher_direction(
    transform: pya.DCplxTrans,
) -> str:
    """
    Estimate launcher direction from transformation angle.

    Parameters
    ----------
    transform:
        Instance transform.
    """

    angle = int(transform.angle) % 360

    if angle == 0:
        return "east"

    if angle == 90:
        return "north"

    if angle == 180:
        return "west"

    return "south"


def expand_box(
    box: pya.DBox,
    margin: float,
) -> pya.DBox:
    """
    Expand a bounding box by a margin.

    Parameters
    ----------
    box:
        Original box.

    margin:
        Margin in micrometers.
    """

    return pya.DBox(
        box.left - margin,
        box.bottom - margin,
        box.right + margin,
        box.top + margin,
    )


def scrape_ports(
    layout: pya.Layout,
    top_cell: pya.Cell,
    box: pya.DBox,
) -> list:
    """
    Scrape launchers and qubits from hierarchy.

    Parameters
    ----------
    layout:
        Layout object.

    top_cell:
        Top cell.

    box:
        Simulation bounding box.
    """

    ports = []

    edge_port_number = 1
    internal_port_number = 100

    for item in iter_instances(layout, top_cell):

        inst = item.instance
        transform = item.transform

        pcell = inst.pcell_declaration()

        if pcell is None:
            continue

        child_cell = layout.cell(inst.cell_index)

        refpoints = get_instance_refpoints(
            layout,
            child_cell,
        )

        if isinstance(pcell, Launcher):

            direction = determine_launcher_direction(
                transform
            )

            base = transform * refpoints["base"]

            port = create_edge_port(
                edge_port_number,
                base,
                direction,
                box,
            )

            ports.append(port)

            edge_port_number += 1

        elif isinstance(pcell, Qubit):

            try:
                inst["junction_type"] = "Sim"

            except Exception:
                pass

            signal_location = (
                transform
                * refpoints["squid_port_squid_a"]
            )

            ground_location = (
                transform
                * refpoints["squid_port_squid_b"]
            )

            ports.append(
                InternalPort(
                    number=internal_port_number,
                    signal_location=signal_location,
                    ground_location=ground_location,
                )
            )

            internal_port_number += 1

    return ports


def clone_layout_to_new_view(
    source_view: KLayoutView,
) -> tuple[KLayoutView, pya.Cell]:
    """
    Clone the active layout into a new KLayout tab.

    Parameters
    ----------
    source_view:
        Original view.
    """

    new_view = KLayoutView()

    source_layout = source_view.layout
    target_layout = new_view.layout

    top_cell = source_view.active_cell

    copied_index = target_layout.copy_tree(
        source_layout,
        top_cell.cell_index(),
    )

    copied_cell = target_layout.cell(copied_index)

    new_view.select_cell(
        copied_cell.cell_index(),
        0,
    )

    return new_view, copied_cell


def main() -> None:
    """Export active GUI layout into Elmer simulation."""

    source_view = KLayoutView(current=True)

    if source_view is None:
        raise RuntimeError(
            "No active KLayout view available."
        )

    top_cell = source_view.active_cell

    if top_cell is None:
        raise RuntimeError(
            "No active top cell found."
        )

    preview_view, preview_cell = (
        clone_layout_to_new_view(source_view)
    )

    layout = preview_view.layout

    box = expand_box(
        preview_cell.dbbox(),
        MARGIN,
    )

    ports = scrape_ports(
        layout,
        preview_cell,
        box,
    )

    if not ports:
        raise RuntimeError(
            "No launchers or qubits detected."
        )

    simulation = Simulation.from_cell(
        preview_cell,
        margin=MARGIN,
        name=EXPORT_NAME,
        box=box,
        ports=ports,
    )

    EXPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    export_elmer(
        [(simulation, solution)],
        path=EXPORT_DIR,
        workflow=workflow,
    )

    preview_view.focus()

    print()
    print("===================================")
    print("Elmer export completed successfully")
    print("===================================")
    print()
    print(f"Export directory: {EXPORT_DIR}")
    print()


if __name__ == "__main__":
    main()
