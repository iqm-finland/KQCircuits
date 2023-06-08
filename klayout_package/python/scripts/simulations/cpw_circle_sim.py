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

from math import pi
from kqcircuits.elements.waveguide_coplanar_curved import WaveguideCoplanarCurved
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.simulation_export import export_simulation_oas
from kqcircuits.simulations.port import InternalPort

from kqcircuits.simulations.simulation import Simulation
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout, \
    open_with_klayout_or_default_application
from kqcircuits.util.parameters import Param, pdt


class CpwCircleSim(Simulation):

    length = Param(pdt.TypeDouble, "Length of coplanar waveguide", 1000, unit="μm")

    def build(self):
        # Create circular waveguide
        r = self.length / (2 * pi)
        trans = pya.DTrans(0, False, self.box.center())
        self.insert_cell(WaveguideCoplanarCurved, trans=trans, alpha=2*pi, r=r)

        # Add an internal port
        ground_point = self.box.center() + pya.DVector(r - self.a / 2 - self.b, 0.0)
        signal_point = self.box.center() + pya.DVector(r - self.a / 2, 0.0)
        self.ports.append(InternalPort(0, signal_point, ground_point))


# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

sim_class = CpwCircleSim  # pylint: disable=invalid-name

# Simulation parameters, using multiface interdigital as starting point
sim_parameters = {
    'name': 'cpw_circle',
    'box': pya.DBox(pya.DPoint(0, 0), pya.DPoint(2000, 2000)),
    "a": 10,
    "b": 6,
    "n": 256,
    "length": 3000,
    "material_dict": {'silicon': {'permittivity': 11.43}}
}
use_elmer = True

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# Simulation sweep
simulations = [sim_class(layout, **sim_parameters)]

# Export Ansys files
if use_elmer:
    export_parameters = {
        'path': dir_path,
        'tool': 'capacitance',
        'linear_system_method': 'mg',
    }
    mesh_size = {
        'global_max': 200.,
        'gap&signal': 2.,
        'gap&ground': 2.,
    }
    workflow = {
        'run_gmsh_gui': True,  # For GMSH: if true, the mesh is shown after it is done
        'run_elmergrid': True,
        'run_elmer': True,
        'run_paraview': True,  # this is visual view of the results which can be removed to speed up the process
        'gmsh_n_threads': -1,  # -1 means all the physical cores
        'elmer_n_processes': -1,  # -1 means all the physical cores
    }
    export_elmer(
        simulations,
        **export_parameters,
        mesh_size=mesh_size,
        workflow=workflow,
        # Uncomment for adaptive meshing
        percent_error=0.005,
        maximum_passes=3,
        minimum_passes=2
    )
else:
    export_parameters = {
        'path': dir_path,
        'ansys_tool': 'q3d',
        'exit_after_run': True,
        'percent_error': 0.1,
        'maximum_passes': 20,
        'minimum_passes': 15,
        'sweep_enabled': False
    }
    export_ansys(simulations, **export_parameters)

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
