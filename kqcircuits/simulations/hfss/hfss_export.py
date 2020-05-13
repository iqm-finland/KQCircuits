import json
from pathlib import Path
from typing import List

from kqcircuits.simulations.hfss.geometry_json_encoder import GeometryJsonEncoder
from kqcircuits.simulations.port import EdgePort, InternalPort
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.simulations.hfss.util import get_enclosing_polygon, find_edge_from_point, export_layers

class HfssExport:
    PARAMETERS = ['port_width', 'port_height', 'substrate_height', 'box_height', 'epsilon']

    port_width = 400.0
    port_height = 1000.0
    substrate_height = 500.0
    box_height = 1000.0
    epsilon = 11.43
    path = None
    file_prefix = ''

    def __init__(self, simulation: Simulation, **kwargs):
        self.simulation = simulation

        if 'file_prefix' not in kwargs:
            self.file_prefix = self.simulation.name
        else:
            self.file_prefix = kwargs['file_prefix']

        if 'path' in kwargs:
            self.path = Path(kwargs['path'])

        for p in self.PARAMETERS:
            if p in kwargs:
                setattr(self, p, kwargs[p])

    @property
    def gds_filename(self):
        return self.path.joinpath(self.file_prefix + '.gds')

    @property
    def oas_filename(self):
        return self.path.joinpath(self.file_prefix + '.oas')

    @property
    def json_filename(self):
        return self.path.joinpath(self.file_prefix + '.json')

    def write(self):
        port_data = self.get_port_data()

        hfss_data = {
            'gds_file': self.gds_filename.parts[-1],
            'signal_layer': self.simulation.ls.layer,
            'ground_layer': self.simulation.lg.layer,
            'units': 'um',  # hardcoded assumption in multiple places
            'substrate_height': self.substrate_height,
            'box_height': self.box_height,
            'epsilon': self.epsilon,
            'box': self.simulation.box,
            'ports': port_data,
            'parameters': self.simulation.get_parameters(),
        }

        if not self.path.exists():
            self.path.mkdir()

        with open(str(self.json_filename), 'w') as fp:
            json.dump(hfss_data, fp, cls=GeometryJsonEncoder, indent=4)

        export_layers(str(self.gds_filename), self.simulation.layout, [self.simulation.cell],
                      output_format='GDS2',
                      layers={self.simulation.ls, self.simulation.lg})

        export_layers(str(self.oas_filename), self.simulation.layout, [self.simulation.cell],
                      output_format='OASIS',
                      layers=None)

    def get_port_data(self):
        port_data = []
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
                signal_edge = find_edge_from_point(
                    self.simulation.cell,
                    self.simulation.layout.layer(self.simulation.ls),
                    port.signal_location,
                    self.simulation.layout.dbu)

                ground_edge = find_edge_from_point(
                    self.simulation.cell,
                    self.simulation.layout.layer(self.simulation.lg),
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
            else Path(__file__).parents[3].joinpath('simulation_scripts/hfss')

        self.import_script = kwargs['import_script'] if 'import_script' in kwargs else 'import_and_simulate.py'
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
            for export in self.exports:
                command = '"{}" -scriptargs "{}" -{} "{}"\n'.format(
                    self.ansys_executable,
                    export.json_filename.name if self.use_rel_path else str(export.json_filename),
                    run_cmd,
                    str(self.import_script_path.joinpath(self.import_script)))
                file.write(command)
            file.write("PAUSE\n")
