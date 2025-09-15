# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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


import logging
import argparse
import sys
import itertools
from pathlib import Path

import pya
import numpy as np

from kqcircuits.elements.element import Element
from kqcircuits.simulations.cross_section_simulation import CrossSectionSimulation
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.simulation_export import export_simulation_oas, cross_sweep_simulation
from kqcircuits.simulations.post_process import PostProcess
from kqcircuits.simulations.simulation import Simulation

from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)
from kqcircuits.util.parameters import add_parameters_from, Param, pdt


@add_parameters_from(Element, "a", "b")
@add_parameters_from(
    Simulation,
    "box",
    metal_height=[0.2],
    vertical_over_etching=0,
    tls_layer_material=["MA", "MS", "SA"],
    tls_layer_thickness=[0.0048, 0.0003, 0.0024],
    material_dict={
        "silicon": {"permittivity": 11.45},
        "MA": {"permittivity": 8.0},
        "MS": {"permittivity": 11.4},
        "SA": {"permittivity": 4.0},
    },
)
class CpwCrossSectionSim(CrossSectionSimulation):

    number_of_cpws = Param(pdt.TypeInt, "Number of co-planar waveguides.", 1)
    cpw_distance = Param(pdt.TypeDouble, "Distance between nearest co-planar waveguides.", 50, unit="μm")
    is_axisymmetric = Param(pdt.TypeBoolean, "Draw half of a CPW for Axi Symmetric case", False)

    def build(self):
        cx = self.box.left if self.is_axisymmetric else self.box.center().x
        cy = self.box.center().y

        # substrate
        substrate = pya.Region(
            pya.DBox(pya.DPoint(self.box.left, self.box.bottom), pya.DPoint(self.box.right, cy)).to_itype(
                self.layout.dbu
            )
        )

        # ground
        metal_thickness = Simulation.ith_value(self.metal_height, 0)
        ground = pya.Region(
            pya.DBox(pya.DPoint(self.box.left, cy), pya.DPoint(self.box.right, cy + metal_thickness)).to_itype(
                self.layout.dbu
            )
        )

        # signals (update substrate and ground accordingly)
        signals = []
        for i in range(self.number_of_cpws):
            sx = cx + self.cpw_distance * (i + (1 - self.number_of_cpws) / 2)
            signals.append(
                pya.Region(
                    pya.DBox(
                        pya.DPoint(sx if self.is_axisymmetric else (sx - self.a / 2), cy),
                        pya.DPoint(sx + self.a / 2, cy + metal_thickness),
                    ).to_itype(self.layout.dbu)
                )
            )
            ground -= pya.Region(
                pya.DBox(
                    pya.DPoint(sx - self.a / 2 - self.b, cy),
                    pya.DPoint(sx + self.a / 2 + self.b, cy + metal_thickness),
                ).to_itype(self.layout.dbu)
            )
            substrate -= pya.Region(
                pya.DBox(
                    pya.DPoint(sx - self.a / 2 - self.b, cy - self.vertical_over_etching),
                    pya.DPoint(sx - self.a / 2, cy),
                ).to_itype(self.layout.dbu)
            )
            substrate -= pya.Region(
                pya.DBox(
                    pya.DPoint(sx + self.a / 2, cy - self.vertical_over_etching),
                    pya.DPoint(sx + self.a / 2 + self.b, cy),
                ).to_itype(self.layout.dbu)
            )

        # interface layers
        if_thickness = [Simulation.ith_value(self.tls_layer_thickness, i) for i in range(3)]
        if_layer = {}
        if any(if_thickness):
            box_region = pya.Region(self.box.to_itype(self.layout.dbu))
            metals = pya.Region()
            for s in signals:
                metals += s
            metals += ground
            if_layer["ma"] = (metals.sized(if_thickness[0] / self.layout.dbu + 0.5) - substrate - metals) & box_region
            if_layer["ms"] = metals.sized(if_thickness[1] / self.layout.dbu + 0.5) & substrate
            substrate -= if_layer["ms"]
            if_layer["sa"] = (
                (substrate.sized(if_thickness[2] / self.layout.dbu + 0.5) & box_region)
                - substrate
                - metals
                - if_layer["ma"]
                - if_layer["ms"]
            )

        # Insert shapes
        self.insert_layer("substrate", substrate, "silicon")
        for i, reg in enumerate(signals, 1):
            self.insert_layer(f"signal_{i}", reg, "pec", excitation=i)
        self.insert_layer("ground", ground, "pec", excitation=0)

        for i, (key, reg) in enumerate(if_layer.items()):
            self.insert_layer(f"{key}_layer", reg, Simulation.ith_value(self.tls_layer_material, i))

        self.insert_layer("vacuum", self.get_unfilled_region(self.box), "vacuum")


parser = argparse.ArgumentParser()
parser.add_argument("--number-of-cpws", nargs="+", default=[1, 2], type=int, help="number of guides in simulations")
parser.add_argument(
    "--vertical-over-etching", nargs="+", default=[0], type=float, help="Vertical over eching in simulations"
)
parser.add_argument("--p-element-order", default=2, type=int, help="Order of p-elements in the FEM computation")
parser.add_argument("--is-axisymmetric", action="store_true", help="Make an axi-symmetric model")
parser.add_argument("--axisymmetric-test", action="store_true", help="Run only one test for axisymmetric case")

args, unknown = parser.parse_known_args()

args.is_axisymmetric = args.axisymmetric_test or args.is_axisymmetric

# Prepare output directory
dir_path = create_or_empty_tmp_directory(f"{Path(__file__).stem}_output")

SimClass = CpwCrossSectionSim

# Simulate Axi-symmetric case with toroidal revolution symmetry
is_axisymmetric = args.is_axisymmetric

# Simulation parameters
sim_parameters = {
    "name": "cpw_cross_section",
    "box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(100, 100)),
    "is_axisymmetric": is_axisymmetric,
    "tls_layer_thickness": [0.0048, 0.003, 0.0024],  # too thin layer would give error in Ansys, so ms is increased
}

mesh_size = {
    "vacuum": 10,
    "substrate": 5,
    "signal_*": 0.1,
    "ground": 0.1,
    "ma_layer": 0.1,
    "ms_layer": 0.1,
    "sa_layer": [0.03, None, 0.3],
}
if is_axisymmetric:
    axi_symmetric_mesh_factor = 4
    mesh_size = {k: v * axi_symmetric_mesh_factor for k, v in mesh_size.items()}
    mesh_size["sa_layer"] = [0.03 * axi_symmetric_mesh_factor, None, 0.3 * axi_symmetric_mesh_factor]

workflow = {
    "run_gmsh": True,
    "run_gmsh_gui": False,
    "run_elmergrid": True,
    "run_elmer": True,
    "run_paraview": False,
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()
layout.dbu = 1e-5  # need finer DBU for SA-interface

# Create simulations
simulations = cross_sweep_simulation(
    layout,
    SimClass,
    sim_parameters,
    {
        "number_of_cpws": args.number_of_cpws,
        "vertical_over_etching": args.vertical_over_etching,
    },
)

# Test large geometries
if is_axisymmetric:
    simulations = [
        SimClass(
            layout,
            **{
                **sim_parameters,
                "a": 2 * r_inner,
                "b": r_outer - r_inner,
                "box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(1500, 1500)),
                "name": f'{sim_parameters["name"]}_{r_inner}_{r_outer - r_inner}',
            },
        )
        for r_inner, r_outer in itertools.product([80], np.arange(60 + 50, 700, step=50, dtype=float))
    ]

    simulations = [simulations[0]] if args.axisymmetric_test else simulations


# Export simulation files
use_elmer = False
if use_elmer:
    export_elmer(
        simulations,
        dir_path,
        tool="cross-section",
        mesh_size=mesh_size,
        workflow=workflow,
        p_element_order=args.p_element_order,
        linear_system_method="mg",
        is_axisymmetric=is_axisymmetric,
        integrate_energies=True,
        post_process=PostProcess("produce_epr_table.py", groups=["ma", "ms", "sa", "substrate", "vacuum"]),
    )
else:
    export_ansys(
        simulations,
        dir_path,
        ansys_tool="cross-section",
        percent_error=0.001,
        maximum_passes=20,
        exit_after_run=True,
        integrate_energies=True,
        post_process=PostProcess("produce_epr_table.py", groups=["ma", "ms", "sa", "substrate", "vacuum"]),
    )

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
