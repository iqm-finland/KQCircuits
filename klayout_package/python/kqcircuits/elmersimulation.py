```python
# -*- coding: utf-8 -*-

"""
KLayout macro:
Export current GUI layout into Elmer simulation.

Suggested location:
klayout_package/python/scripts/macros/export/export_elmer.lym
"""

from pathlib import Path

import pya

from kqcircuits.pya_resolver import pya
from kqcircuits.klayout_view import KLayoutView

from kqcircuits.defaults import default_layers
from kqcircuits.util.refpoints import get_refpoints

from kqcircuits.elements.launcher import Launcher
from kqcircuits.qubits.qubit import Qubit

from kqcircuits.simulations.simulation import Simulation
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer

from kqcircuits.simulations.port import EdgePort, InternalPort
from kqcircuits.simulations.export.util import refine_metal_edges

from kqcircuits.simulations.export.elmer.elmer_solution import (
    ElmerVectorHelmholtzSolution,
)


# ============================================================
# USER CONFIGURATION
# ============================================================

SIMULATION_NAME = "gui_export"

EXPORT_PATH = (
    Path.home()
    / "KQCircuits"
    / "tmp"
    / f"{SIMULATION_NAME}_elmer"
)

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


# ============================================================
# HIERARCHY SCRAPER
# ============================================================

def scrape_instances(
    layout,
    cell,
    trans,
    ports,
    launcher_edges,
    internal_port_number,
):
    """
    Recursively scrape hierarchy for launchers and qubits.
    """

    ref_layer = layout.layer(default_layers["refpoints"])

    for inst in cell.each_inst():

        child_cell = layout.cell(inst.cell_index)

        current_trans = trans * inst.dcplx_trans

        pcell = inst.pcell_declaration()

        if pcell is None:
            scrape_instances(
                layout,
                child_cell,
                current_trans,
                ports,
                launcher_edges,
                internal_port_number,
            )
            continue

        # ----------------------------------------------------
        # Launchers -> EdgePorts
        # ----------------------------------------------------

        if isinstance(pcell, Launcher):

            refpoints = get_refpoints(ref_layer, child_cell)

            # Adjust according to launcher implementation
            if "port" in refpoints:
                port_point = current_trans * refpoints["port"]
            else:
                port_point = current_trans * refpoints["base"]

            launcher_edges.append(port_point)

        # ----------------------------------------------------
        # Qubits -> InternalPorts
        # ----------------------------------------------------

        if isinstance(pcell, Qubit):

            # Force simulation junctions
            try:
                inst["junction_type"] = "Sim"
            except Exception:
                pass

            refpoints = get_refpoints(ref_layer, child_cell)

            if (
                "squid_port_squid_a" in refpoints
                and "squid_port_squid_b" in refpoints
            ):

                signal_pt = (
                    current_trans
                    * refpoints["squid_port_squid_a"]
                )

                ground_pt = (
                    current_trans
                    * refpoints["squid_port_squid_b"]
                )

                ports.append(
                    InternalPort(
                        number=internal_port_number[0],
                        signal_location=signal_pt,
                        ground_location=ground_pt,
                    )
                )

                internal_port_number[0] += 1

        # recurse
        scrape_instances(
            layout,
            child_cell,
            current_trans,
            ports,
            launcher_edges,
            internal_port_number,
        )


# ============================================================
# BOX ALIGNMENT
# ============================================================

def determine_box(top_cell, launcher_points, margin=100):

    bbox = top_cell.dbbox()

    left = bbox.left
    right = bbox.right
    top = bbox.top
    bottom = bbox.bottom

    tolerance = 200

    # Snap edges to launcher locations
    for p in launcher_points:

        if abs(p.x - left) < tolerance:
            left = p.x

        if abs(p.x - right) < tolerance:
            right = p.x

        if abs(p.y - top) < tolerance:
            top = p.y

        if abs(p.y - bottom) < tolerance:
            bottom = p.y

    return pya.DBox(
        left - margin,
        bottom - margin,
        right + margin,
        top + margin,
    )


# ============================================================
# EDGE PORT CREATION
# ============================================================

def create_edge_ports(box, launcher_points, start_index=1):

    ports = []

    tol = 1e-3

    for i, p in enumerate(launcher_points):

        side = None

        if abs(p.x - box.left) < tol:
            side = "left"

        elif abs(p.x - box.right) < tol:
            side = "right"

        elif abs(p.y - box.top) < tol:
            side = "top"

        elif abs(p.y - box.bottom) < tol:
            side = "bottom"

        if side is None:
            raise RuntimeError(
                f"Launcher at {p} is not on simulation boundary."
            )

        ports.append(
            EdgePort(
                number=start_index + i,
                signal_location=p,
                side=side,
            )
        )

    return ports


# ============================================================
# MAIN
# ============================================================

view = KLayoutView(current=True)

top_cell = view.active_cell
layout = view.layout

if top_cell is None:
    raise RuntimeError("No active cell.")

# ------------------------------------------------------------
# Create separate preview layout
# ------------------------------------------------------------

preview_view = KLayoutView()

layout_copy = preview_view.layout

top_copy = layout_copy.create_cell(top_cell.name)

top_copy.copy_tree(top_cell)

preview_view.insert_cell(top_copy)

# ------------------------------------------------------------
# Extract ports
# ------------------------------------------------------------

ports = []

launcher_points = []

internal_port_number = [100]

scrape_instances(
    layout_copy,
    top_copy,
    pya.DCplxTrans(),
    ports,
    launcher_points,
    internal_port_number,
)

# ------------------------------------------------------------
# Determine box
# ------------------------------------------------------------

box = determine_box(top_copy, launcher_points)

# ------------------------------------------------------------
# Create edge ports
# ------------------------------------------------------------

edge_ports = create_edge_ports(box, launcher_points)

ports.extend(edge_ports)

# ------------------------------------------------------------
# Build simulation
# ------------------------------------------------------------

simulation = Simulation.from_cell(
    top_copy,
    margin=100,
    name=SIMULATION_NAME,
    box=box,
    ports=ports,
)

# ------------------------------------------------------------
# Export
# ------------------------------------------------------------

EXPORT_PATH.mkdir(parents=True, exist_ok=True)

export_elmer(
    [(simulation, solution)],
    EXPORT_PATH,
    workflow=workflow,
)

print("")
print("======================================")
print("Elmer export complete")
print(f"Export path: {EXPORT_PATH}")
print("======================================")
print("")
```
