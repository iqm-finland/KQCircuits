from abc import ABCMeta, abstractmethod
from pathlib import Path

from kqcircuits.simulations.simulation import Simulation


class SimulationExport(metaclass=ABCMeta):
    PARAMETERS = ['substrate_height', 'substrate_height_2', 'chip_distance' 
                  'box_height', 'wafer_stack_type', 'epsilon', 'airbridge_height']

    # default values for parameters
    substrate_height = 550.0        # realistic bottom substrate thickness
    substrate_height_2 = 375.0      # realistic top substrate thickness
    airbridge_height = 3.4
    chip_distance = 8.
    box_height = 1000.0
    epsilon = 11.43
    wafer_stack_type = "planar"
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

        for p in self.PARAMETERS:
            if p in kwargs:
                setattr(self, p, kwargs[p])

    @abstractmethod
    def write(self):
        pass

    @property
    def oas_filename(self):
        return self.path.joinpath(self.file_prefix + '.oas')
