import logging
from pathlib import Path

from kqcircuits.defaults import default_layers
from kqcircuits.simulations.port import InternalPort
from kqcircuits.simulations.simulation import Simulation
import kqcircuits.simulations.sonnet.parser as sonnet
import kqcircuits.simulations.sonnet.simgeom as simgeom
import os.path


class SonnetExport:
    PARAMETERS = ['detailed_resonance', 'lower_accuracy', 'control', 'current',
                  'fill_type', 'simulation_safety']

    path = None
    file_prefix = ''

    def __init__(self, simulation: Simulation, auto_port_detection: bool, **kwargs):
        if simulation is None or not isinstance(simulation, Simulation):
            raise ValueError("Cannot export without simulation")
        self.simulation = simulation

        if auto_port_detection is None or not isinstance(auto_port_detection, bool):
            raise ValueError("Please set the auto_port_detection")
        self.auto_port_detection = auto_port_detection

        if 'file_prefix' not in kwargs:
            self.file_prefix = self.simulation.name
        else:
            self.file_prefix = kwargs['file_prefix']

        if 'path' in kwargs:
            self.path = Path(kwargs['path'])
        else:
            self.path = os.getcwd()

        if 'materials_type' in kwargs:
            self.materials_type = kwargs['materials_type']
        else:
            self.materials_type = "Si BT" # i.e. does not have airbridges

        for p in self.PARAMETERS:
            if p in kwargs:
                setattr(self, p, kwargs[p])

    @property
    def son_filename(self):
        return self.path.joinpath(self.file_prefix + '.son')

    def write(self):
        ports = []
        refpoints = self.simulation.get_refpoints(self.simulation.cell)
        refpoints_sonnet = dict(filter(lambda e: "sonnet_port" in e[0], refpoints.items()))
        refpoints = dict(filter(lambda e: "port" in e[0], refpoints.items()))
        i = 1 # Sonnet indexing starts from 1

        if (self.auto_port_detection):
            # This turns all ports to Sonnet ports
            for portname, location in refpoints.items():
                ports.append(InternalPort(i, location, location, group=""))
                i += 1
        else:
            # This turns only the annotations named "sonnet_port" to Sonnet ports
            for portname, location in refpoints_sonnet.items():
                ports.append(InternalPort(i, location, location, group=""))
                i += 1
        logging.info("Port reference points: " + str(i-1))

        self.simulation.create_simulation_layers() # update ls lg

        if not self.path.exists():
            self.path.mkdir()

        # sonnet calibration groups, currently do manually in sonnet
        calgroup = "CUPGRP \"A\"\nID 28\nGNDREF F\nTWTYPE FEED\nEND"

        shapes_in_air = self.simulation.layout.begin_shapes(self.simulation.cell, self.simulation.layout.layer(default_layers["b airbridge flyover"]))
        materials_type = "Si+Al" if not shapes_in_air.shape().is_null() else "Si BT"

        # defaults if not in parameters
        self.detailed_resonance = getattr(self, 'detailed_resonance', False)
        self.lower_accuracy = getattr(self, 'lower_accuracy', False)
        self.current = getattr(self, 'current', False)
        self.control = getattr(self, 'control', 'ABS')
        self.fill_type = getattr(self, 'fill_type', 'Staircase')
        self.simulation_safety = getattr(self, 'simulation_safety', 0) # microns


        sonnet_strings = simgeom.add_sonnet_geometry(
          cell = self.simulation.cell,
          ls = self.simulation.ls,
          materials_type = materials_type,
          simulation_safety = self.simulation_safety, # microns
          ports = ports,
          calgroup = calgroup,
          grid_size = 1, # microns
          symmetry = False, # top-bottom symmetry for sonnet -> could be 4-8x faster
          detailed_resonance = self.detailed_resonance,
          lower_accuracy = self.lower_accuracy,
          current = self.current,
          fill_type = self.fill_type
          )
        sonnet_strings["control"] = sonnet.control(self.control)

        filename = str(self.son_filename)
        sonnet.apply_template(
          os.path.join(os.path.dirname(os.path.abspath(sonnet.__file__)), "template.son"),
          filename,
          sonnet_strings
          )
