# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
from itertools import product
from pathlib import Path

from kqcircuits.simulations.export.util import export_layers


def export_simulation_oas(simulations, path: Path, file_prefix='simulation'):
    """
    Write single OASIS file containing all simulations in list.
    """
    unique_layouts = set([simulation.layout for simulation in simulations])
    if len(unique_layouts) != 1:
        raise ValueError("Cannot write batch OASIS file since not all simulations are on the same layout.")

    cells = [simulation.cell for simulation in simulations]
    oas_filename = str(path.joinpath(file_prefix + '.oas'))
    export_layers(oas_filename, simulations[0].layout, cells,
                  output_format='OASIS',
                  layers=None)
    return oas_filename


def sweep_simulation(layout, sim_class, sim_parameters, sweeps):
    """Create simulation sweep by varying one parameter at time. Return list of simulations."""
    simulations = []
    for param in sweeps:
        for value in sweeps[param]:
            parameters = {**sim_parameters, param: value,
                          'name': '{}_{}_{}'.format(sim_parameters['name'], param, value)}
            simulations.append(sim_class(layout, **parameters))
    return simulations


def cross_sweep_simulation(layout, sim_class, sim_parameters, sweeps):
    """Create simulation sweep by cross varying all parameters. Return list of simulations."""
    simulations = []
    keys = [key for key in sweeps]
    sets = [list(prod) for prod in product(*sweeps.values())]
    for values in sets:
        parameters = {**sim_parameters}
        for i in range(len(keys)):
            parameters[keys[i]] = values[i]
        parameters['name'] = sim_parameters['name'] + '_' + '_'.join([str(value) for value in values])
        simulations.append(sim_class(layout, **parameters))
    return simulations
