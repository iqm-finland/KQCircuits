from pathlib import Path

from kqcircuits.defaults import default_layers
from kqcircuits.simulations.port import InternalPort
from kqcircuits.simulations.simulation import Simulation
import kqcircuits.simulations.sonnet.parser as sonnet
import kqcircuits.simulations.sonnet.simgeom as simgeom
import os.path


class SonnetExport:
    PARAMETERS = ['port_width', 'port_height', 'substrate_height', 'box_height', 'epsilon'] # examples for now

    path = None
    file_prefix = ''

    def __init__(self, simulation: Simulation, **kwargs):
        if simulation is None or not isinstance(simulation, Simulation):
            raise ValueError("Cannot export without simulation")
        self.simulation = simulation

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
        refpoints = dict(filter(lambda e: "port" in e[0], refpoints.items()))

        i = 1 # Sonnet indexing starts from 1
        for portname, location in refpoints.items():
            ports.append(InternalPort(i, location, location, group=""))
            i += 1
        print("Port reference points: " + str(i-1))

        self.simulation.create_simulation_layers() # update ls lg

        if not self.path.exists():
            self.path.mkdir()

        # sonnet calibration groups, currently do manually in sonnet
        calgroup = "CUPGRP \"A\"\nID 28\nGNDREF F\nTWTYPE FEED\nEND"
        simulation_safety = 3*300 # microns, hard coded for now

        shapes_in_air = self.simulation.layout.begin_shapes(self.simulation.cell, self.simulation.layout.layer(default_layers["b airbridge flyover"]))
        materials_type = "Si+Al" if not shapes_in_air.shape().is_null() else "Si BT"


        sonnet_strings = simgeom.add_sonnet_geometry(
          cell = self.simulation.cell,
          ls = self.simulation.ls, # TODO also ground layer
          materials_type = materials_type,
          simulation_safety = simulation_safety, # microns
          ports = ports,
          calgroup = calgroup,
          grid_size = 1, # microns
          symmetry = False # top-bottom symmetry for sonnet -> would be 4-8x faster
        )
        sonnet_strings["control"] = sonnet.control("ABS")

        filename = str(self.son_filename)
        sonnet.apply_template(
          os.path.join(os.path.dirname(os.path.abspath(sonnet.__file__)), "template.son"),
          filename,
          sonnet_strings
          )
