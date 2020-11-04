# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import json
from pathlib import Path
from typing import List

from kqcircuits.util.geometry_json_encoder import GeometryJsonEncoder
from kqcircuits.simulations.port import EdgePort, InternalPort
from kqcircuits.simulations.export.util import get_enclosing_polygon, find_edge_from_point_in_cell, export_layers
from kqcircuits.defaults import default_layers
from kqcircuits.simulations.export.simulation_export import SimulationExport


class HfssExport(SimulationExport):
    PARAMETERS = [
        *SimulationExport.PARAMETERS,
        'port_width', 'port_height',
        'frequency_units', 'frequency', 'max_delta_s', 'maximum_passes', 'minimum_passes', 'minimum_converged_passes',
        'sweep_enabled', 'sweep_start', 'sweep_end', 'sweep_count'
    ]

    # default values for parameters
    port_width = 400.0
    port_height = 1000.0
    frequency_units = "GHz"
    frequency = 5
    max_delta_s = 0.1
    maximum_passes = 12
    minimum_passes = 1
    minimum_converged_passes = 1
    sweep_enabled = True
    sweep_start = 0
    sweep_end = 10
    sweep_count = 101

    @property
    def gds_filename(self):
        return self.path.joinpath(self.file_prefix + '.gds')

    @property
    def json_filename(self):
        return self.path.joinpath(self.file_prefix + '.json')

    def write(self):
        port_data = self.get_port_data()

        hfss_data = {
            'gds_file': self.gds_filename.parts[-1],
            'stack_type': self.wafer_stack_type,
            'signal_layer': default_layers["b simulation signal"],
            'ground_layer': default_layers["b simulation ground"],
            'airbridge_flyover_layer': default_layers["b simulation airbridge flyover"],
            'airbridge_pads_layer': default_layers["b simulation airbridge pads"],
            'units': 'um',  # hardcoded assumption in multiple places
            'substrate_height': self.substrate_height,
            'airbridge_height': self.airbridge_height,
            'box_height': self.box_height,
            'epsilon': self.epsilon,
            'box': self.simulation.box,
            'ports': port_data,
            'parameters': self.simulation.get_parameters(),
            'analysis_setup': {
                'frequency_units': self.frequency_units,
                'frequency': self.frequency,
                'max_delta_s': self.max_delta_s,
                'maximum_passes': self.maximum_passes,
                'minimum_passes': self.minimum_passes,
                'minimum_converged_passes': self.minimum_converged_passes,
                'sweep_enabled': self.sweep_enabled,
                'sweep_start': self.sweep_start,
                'sweep_end': self.sweep_end,
                'sweep_count': self.sweep_count
            }
        }
        if self.wafer_stack_type == "multiface":
            hfss_data = {**hfss_data,
                         "substrate_height_top": self.substrate_height_2,
                         "chip_distance": self.chip_distance,
                         "t_signal_layer": default_layers["t simulation signal"],
                         "t_ground_layer": default_layers["t simulation ground"]
                         }
            optional_layers = {default_layers["t simulation signal"], default_layers["t simulation ground"]}
        else:
            optional_layers = {}

        if not self.path.exists():
            self.path.mkdir()

        with open(str(self.json_filename), 'w') as fp:
            json.dump(hfss_data, fp, cls=GeometryJsonEncoder, indent=4)

        export_layers(str(self.gds_filename), self.simulation.layout, [self.simulation.cell],
                      output_format='GDS2',
                      layers={default_layers["b simulation signal"],
                              default_layers["b simulation ground"],
                              default_layers["b simulation airbridge flyover"],
                              default_layers["b simulation airbridge pads"],
                              *optional_layers}
        )

        export_layers(str(self.oas_filename), self.simulation.layout, [self.simulation.cell],
                      output_format='OASIS',
                      layers=None)

    def get_port_data(self):
        port_data = []
        if self.simulation.use_ports:
            for port in self.simulation.ports:
                # Basic data from Port
                p_data = port.as_dict()

                # Define a 3D polygon for each port
                if isinstance(port, EdgePort):

                    # Determine which edge this port is on
                    if (port.signal_location.x == self.simulation.box.left
                            or port.signal_location.x == self.simulation.box.right):
                        p_data['polygon'] = [
                                        [port.signal_location.x, port.signal_location.y - self.port_width/2, -self.substrate_height],
                                        [port.signal_location.x, port.signal_location.y + self.port_width/2, -self.substrate_height],
                                        [port.signal_location.x, port.signal_location.y + self.port_width/2, -self.substrate_height + self.port_height],
                                        [port.signal_location.x, port.signal_location.y - self.port_width/2, -self.substrate_height + self.port_height]
                        ]

                    elif (port.signal_location.y == self.simulation.box.top
                            or port.signal_location.y == self.simulation.box.bottom):
                        p_data['polygon'] = [
                                        [port.signal_location.x - self.port_width/2, port.signal_location.y, -self.substrate_height],
                                        [port.signal_location.x + self.port_width/2, port.signal_location.y, -self.substrate_height],
                                        [port.signal_location.x + self.port_width/2, port.signal_location.y, -self.substrate_height + self.port_height],
                                        [port.signal_location.x - self.port_width/2, port.signal_location.y, -self.substrate_height + self.port_height]
                        ]

                    else:
                        raise(ValueError, "Port {} is an EdgePort but not on the edge of the simulation box".format(port.number))

                elif isinstance(port, InternalPort):
                    _, _, signal_edge = find_edge_from_point_in_cell(
                        self.simulation.cell,
                        self.simulation.layout.layer(default_layers["b simulation signal"]),
                        port.signal_location,
                        self.simulation.layout.dbu)

                    _, _, ground_edge = find_edge_from_point_in_cell(
                        self.simulation.cell,
                        self.simulation.layout.layer(default_layers["b simulation ground"]),
                        port.ground_location,
                        self.simulation.layout.dbu)

                    p_data['polygon'] = get_enclosing_polygon(
                        [[signal_edge.x1, signal_edge.y1, 0], [signal_edge.x2, signal_edge.y2, 0],
                         [ground_edge.x1, ground_edge.y1, 0], [ground_edge.x2, ground_edge.y2, 0]])
                else:
                    raise(ValueError, "Port {} has unsupported port class {}".format(port.number, type(port).__name__))

                port_data.append(p_data)

        return port_data


class HfssBatch:
    def __init__(self, exports: List[HfssExport], **kwargs):
        self.exports = exports

        self.file_prefix = kwargs['file_prefix'] if 'file_prefix' in kwargs else 'simulation'
        self.path = Path(kwargs['path']) if 'path' in kwargs else None
        self.exit_after_run = kwargs['exit_after_run'] if 'exit_after_run' in kwargs else False

        self.ansys_executable = kwargs['ansys_executable'] if 'ansys_executable' in kwargs \
            else r"%PROGRAMFILES%\AnsysEM\AnsysEM20.1\Win64\ansysedt.exe"

        self.import_script_path = Path(kwargs['import_script_path']) if 'import_script_path' in kwargs \
            else Path(__file__).parents[3].joinpath('scripts/simulations/hfss')

        self.import_script = kwargs['import_script'] if 'import_script' in kwargs else 'import_and_simulate.py'
        self.post_process_script = kwargs['post_process_script'] if 'post_process_script' in kwargs \
            else 'export_batch_results.py'
        self.use_rel_path = kwargs['use_rel_path'] if 'use_rel_path' in kwargs else True

    @property
    def oas_filename(self):
        return self.path.joinpath(self.file_prefix + '.oas')

    @property
    def bat_filename(self):
        return self.path.joinpath(self.file_prefix + '.bat')

    def write_oas(self):
        """
        Write single OASIS file containing all simulations in the batch.
        """

        unique_layouts = set([export.simulation.layout for export in self.exports])
        if len(unique_layouts) != 1:
            raise ValueError("Cannot write batch OASIS file since not all simulations are on the same layout.")

        cells = [export.simulation.cell for export in self.exports]
        export_layers(str(self.oas_filename), self.exports[0].simulation.layout, cells,
                      output_format='OASIS',
                      layers=None)

    def write_batch(self):
        """
        Create a batch file for running one or more already exported simulations in HFSS
        """
        run_cmd = 'RunScriptAndExit' if self.exit_after_run else 'RunScript'

        with open(str(self.bat_filename), 'w') as file:
            # Commands for each simulation
            for export in self.exports:
                command = '"{}" -scriptargs "{}" -{} "{}"\n'.format(
                    self.ansys_executable,
                    export.json_filename.name if self.use_rel_path else str(export.json_filename),
                    run_cmd,
                    str(self.import_script_path.joinpath(self.import_script)))
                file.write(command)

            # Post-process command
            command = '"{}" -{} "{}"\n'.format(
                self.ansys_executable,
                run_cmd,
                str(self.import_script_path.joinpath(self.post_process_script)))
            file.write(command)

            # Pause
            file.write("PAUSE\n")
