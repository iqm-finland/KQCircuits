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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).


import logging
import sys
from pathlib import Path

import pya

from kqcircuits.elements.element import Element
from kqcircuits.simulations.cross_section_simulation import CrossSectionSimulation
from kqcircuits.simulations.export.elmer.cross_section_elmer_export import export_cross_section_elmer
from kqcircuits.simulations.export.simulation_export import export_simulation_oas, sweep_simulation

from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout, \
    open_with_klayout_or_default_application
from kqcircuits.util.parameters import add_parameters_from, Param, pdt


@add_parameters_from(Element, 'a', 'b')
class CpwCrossSectionSim(CrossSectionSimulation):

    number_of_cpws = Param(pdt.TypeInt, "Number of co-planar waveguides.", 1)
    cpw_distance = Param(pdt.TypeDouble, "Distance between nearest co-planar waveguides.", 50, unit="μm")

    vertical_over_etching = Param(pdt.TypeDouble, "Vertical over-etching into substrates at gaps.", 0, unit="μm")
    metal_thickness = Param(pdt.TypeDouble, "Thickness of metal sheets", 0.2, unit='µm')
    oxide_thickness = Param(pdt.TypeDouble, "Thickness of oxide layers", 0.01, unit='µm')

    def build(self):
        cx = self.box.center().x
        cy = self.box.center().y

        # substrate
        substrate = pya.Region(pya.DBox(
            pya.DPoint(self.box.left, self.box.bottom), pya.DPoint(self.box.right, cy)
        ).to_itype(self.layout.dbu))

        # ground
        ground = pya.Region(pya.DBox(
            pya.DPoint(self.box.left, cy), pya.DPoint(self.box.right, cy + self.metal_thickness)
        ).to_itype(self.layout.dbu))

        # signals (update substrate and ground accordingly)
        signals = []
        for i in range(self.number_of_cpws):
            sx = cx + self.cpw_distance * (i + (1 - self.number_of_cpws) / 2)
            signals.append(pya.Region(pya.DBox(
                pya.DPoint(sx - self.a/2, cy), pya.DPoint(sx + self.a/2, cy + self.metal_thickness)
            ).to_itype(self.layout.dbu)))
            ground -= pya.Region(pya.DBox(
                pya.DPoint(sx - self.a/2 - self.b, cy), pya.DPoint(sx + self.a/2 + self.b, cy + self.metal_thickness)
            ).to_itype(self.layout.dbu))
            substrate -= pya.Region(pya.DBox(
                pya.DPoint(sx - self.a/2 - self.b, cy - self.vertical_over_etching), pya.DPoint(sx - self.a/2, cy)
            ).to_itype(self.layout.dbu))
            substrate -= pya.Region(pya.DBox(
                pya.DPoint(sx + self.a/2, cy - self.vertical_over_etching), pya.DPoint(sx + self.a/2 + self.b, cy)
            ).to_itype(self.layout.dbu))

        # oxide layers
        if self.oxide_thickness > 0.0:
            box_region = pya.Region(self.box.to_itype(self.layout.dbu))
            metals = pya.Region()
            for s in signals:
                metals += s
            metals += ground
            i_oxide = self.oxide_thickness / self.layout.dbu
            ma_layer = (metals.sized(i_oxide) - substrate - metals) & box_region
            ms_layer = metals.sized(i_oxide) & substrate
            substrate -= ms_layer
            sa_layer = (substrate.sized(i_oxide) & box_region) - substrate - metals - ms_layer - ma_layer

        # Insert shapes
        self.cell.shapes(self.get_sim_layer("substrate")).insert(substrate)
        self.set_permittivity("substrate", 11.45)
        for i, s in enumerate(signals):
            self.cell.shapes(self.get_sim_layer(f"signal_{i}")).insert(s)
        self.cell.shapes(self.get_sim_layer("ground")).insert(ground)

        if self.oxide_thickness > 0.0:
            self.cell.shapes(self.get_sim_layer("ma_layer")).insert(ma_layer)
            self.set_permittivity("ma_layer", 8.0)
            self.cell.shapes(self.get_sim_layer("ms_layer")).insert(ms_layer)
            self.set_permittivity("ms_layer", 11.4)
            self.cell.shapes(self.get_sim_layer("sa_layer")).insert(sa_layer)
            self.set_permittivity("sa_layer", 4.0)

# Prepare output directory
dir_path = create_or_empty_tmp_directory(f"{Path(__file__).stem}_output")

sim_class = CpwCrossSectionSim  # pylint: disable=invalid-name

# Simulation parameters
sim_parameters = {
    'name': 'cpw_cross_section',
    'box': pya.DBox(pya.DPoint(0, 0), pya.DPoint(100, 100))
}
mesh_size = {
    'vacuum': 10,
    'substrate': 5,
    'signal_0': 0.1,
    'signal_1': 0.1,
    'ground': 0.1,
    'ma_layer': 0.1,
    'ms_layer': 0.1,
    'sa_layer': 0.1
}
workflow = {
    'run_gmsh': True,
    'run_gmsh_gui': True,
    'run_elmergrid': True,
    'run_elmer': True,
    'run_paraview': True,
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# Create simulations
simulations = sweep_simulation(layout, sim_class, sim_parameters, {
    'number_of_cpws': [1, 2],
    'vertical_over_etching': [10]
})

# Export simulation files
export_cross_section_elmer(simulations, dir_path, mesh_size=mesh_size, workflow=workflow)

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
