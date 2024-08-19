# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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
from typing import Sequence

from kqcircuits.simulations.partition_region import get_list_of_two

from kqcircuits.simulations.export.simulation_export import cross_combine

from kqcircuits.simulations.export.elmer.elmer_solution import ElmerCrossSectionSolution

from kqcircuits.defaults import XSECTION_PROCESS_PATH

from kqcircuits.simulations.export.xsection.xsection_export import (
    separate_signal_layer_shapes,
    create_xsections_from_simulations,
    visualise_xsection_cut_on_original_layout,
)

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.post_process import PostProcess


def get_epr_correction_elmer_solution(**override_args):
    """Returns ElmerCrossSectionSolution for EPR correction simulations with default arguments.
    Optionally, 'override_args' can be used to override any arguments.
    """
    return ElmerCrossSectionSolution(
        **{
            "linear_system_method": "mg",
            "p_element_order": 3,
            "is_axisymmetric": False,
            "mesh_size": {
                "ms_layer_mer&ma_layer_mer": [0.0005, 0.0005, 0.2],
            },
            "integrate_energies": True,
            **override_args,
        }
    )


def get_epr_correction_simulations(
    simulations,
    path,
    correction_cuts,
    ma_eps_r=8,
    ms_eps_r=11.4,
    sa_eps_r=4,
    ma_thickness=4.8e-3,  # in µm
    ms_thickness=0.3e-3,  # in µm
    sa_thickness=2.4e-3,  # in µm
    ma_bg_eps_r=1,
    ms_bg_eps_r=11.45,
    sa_bg_eps_r=11.45,
    metal_height=None,
):
    """Helper function to produce EPR correction simulations.

    Args:
        simulations (list): list of simulation objects
        path (Path): path to simulation folder
        correction_cuts (dict): dictionary of correction cuts. Key is the name of cut and values are dicts containing:
        - p1: pya.DPoint indicating the first end of the cut segment
        - p2: pya.DPoint indicating the second end of the cut segment
        - metal_edges: list of dictionaries indicating metal-edge-region locations and orientations in 2D simulation.
            Can contain keywords:
            - x: lateral distance from p1 to mer metal edge,
            - x_reversed: whether gap is closer to p1 than metal, default=False
            - z: height of substrate-vacuum interface, default=0
            - z_reversed: whether vacuum is below substrate, default=False
        - partition_regions: (optional) list of partition region names. The correction cut key is used if not assigned.
        - simulations: (optional) list of simulation names. Is applied on all simulations if not assigned.
        - solution: (optional) solution object for the sim. get_epr_correction_elmer_solution is used if not assigned.
        ma_eps_r (float): relative permittivity of MA layer
        ms_eps_r (float): relative permittivity of MS layer
        sa_eps_r (float): relative permittivity of SA layer
        ma_thickness (float): thickness of MA layer
        ms_thickness (float): thickness of MS layer
        sa_thickness (float): thickness of SA layer
        ma_bg_eps_r (float): rel permittivity at the location of MA layer in 3D simulation (sheet approximation in use)
        ms_bg_eps_r (float): rel permittivity at the location of MS layer in 3D simulation (sheet approximation in use)
        sa_bg_eps_r (float): rel permittivity at the location of SA layer in 3D simulation (sheet approximation in use)
        metal_height (float): height of metal layers in correction simulations. Use None to get heights from 3D stack

    Returns:
        tuple containing list of correction simulations and list of post_process objects
    """
    correction_simulations = []
    correction_layout = pya.Layout()
    source_sims = {sim[0] if isinstance(sim, Sequence) else sim for sim in simulations}
    for source_sim in source_sims:
        if metal_height is not None:
            source_sim.metal_height = metal_height
        separate_signal_layer_shapes(source_sim)

        for key, cut in correction_cuts.items():
            if "simulations" in cut and source_sim.name not in cut["simulations"]:
                continue

            part_names = cut.get("partition_regions", [key])
            if not part_names:
                raise ValueError("Correction cut has no partition region attached")

            parts = [p for p in source_sim.partition_regions if p["name"] in part_names]
            if not parts:
                continue

            v_dims = get_list_of_two(parts[0]["vertical_dimensions"])
            h_dims = get_list_of_two(parts[0]["metal_edge_dimensions"])
            if None in v_dims or any(v_dims != get_list_of_two(p["vertical_dimensions"]) for p in parts):
                raise ValueError(f"Partition region vertical_dimensions are invalid for correction_cut {key}.")
            if None in h_dims or any(h_dims != get_list_of_two(p["metal_edge_dimensions"]) for p in parts):
                raise ValueError(f"Partition region metal_edge_dimensions are invalid for correction_cut {key}.")

            mer_box = []
            for me in cut["metal_edges"]:
                x = me.get("x", 0)
                z = me.get("z", 0)
                dx = int(me.get("x_reversed", False))
                dz = int(me.get("z_reversed", False))
                mer_box.append(pya.DBox(x - h_dims[1 - dx], z - v_dims[dz], x + h_dims[dx], z + v_dims[1 - dz]))

            cords_list = [(cut["p1"], cut["p2"])]
            correction_simulations += cross_combine(
                create_xsections_from_simulations(
                    [source_sim],
                    path,
                    cords_list,
                    layout=correction_layout,
                    ma_permittivity=ma_eps_r,
                    ms_permittivity=ms_eps_r,
                    sa_permittivity=sa_eps_r,
                    ma_thickness=ma_thickness,
                    ms_thickness=ms_thickness,
                    sa_thickness=sa_thickness,
                    magnification_order=1,
                    process_path=XSECTION_PROCESS_PATH,
                    mer_box=mer_box,
                ),
                cut["solution"] if "solution" in cut else get_epr_correction_elmer_solution(),
            )
            correction_simulations[-1][0].name = correction_simulations[-1][0].cell.name = source_sim.name + "_" + key
            visualise_xsection_cut_on_original_layout([source_sim], cords_list, cut_label=key, width_ratio=0.03)

    post_process = [
        PostProcess(
            "produce_epr_table.py",
            data_file_prefix="correction",
            sheet_approximations={
                "MA": {"thickness": ma_thickness * 1e-6, "eps_r": ma_eps_r, "background_eps_r": ma_bg_eps_r},
                "MS": {"thickness": ms_thickness * 1e-6, "eps_r": ms_eps_r, "background_eps_r": ms_bg_eps_r},
                "SA": {"thickness": sa_thickness * 1e-6, "eps_r": sa_eps_r, "background_eps_r": sa_bg_eps_r},
            },
            groups=["MA", "MS", "SA", "substrate", "vacuum"],
            region_corrections={
                **{p["name"]: None for s in source_sims for p in s.partition_regions},
                **{p: k for k, v in correction_cuts.items() for p in v.get("partition_regions", [k])},
            },
        ),
    ]
    return correction_simulations, post_process
