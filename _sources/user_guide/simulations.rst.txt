External simulation tools
=========================

KQCircuits supports exports to following external simulation tools:

* `Ansys Electronics desktop <https://www.ansys.com/products/electronics>`_ (`HFSS <https://www.ansys.com/products/electronics/ansys-hfss>`_ and `Q3D Extractor <https://www.ansys.com/products/electronics/ansys-q3d-extractor>`_)
* `Gmsh <https://gmsh.info>`_ and `Elmer <http://www.elmerfem.org>`_
* `Sonnet <https://www.sonnetsoftware.com>`_

The main feature in KQCircuits simulation framework is the ability to export geometries from designed layouts into
the format required by the external simulation tool.
The geometry is described by a **simulation object**, which is typically an instances of a dedicated subclass of either
:class:`.Simulation` or :class:`.CrossSectionSimulation`.

The geometry described by a simulation object can be exported to any of above external simulation tool using a
tool-specific **export function**. Namely, these are

   * :func:`~kqcircuits.simulations.export.ansys.ansys_export.export_ansys`,
   * :func:`~kqcircuits.simulations.export.elmer.elmer_export.export_elmer`,
   * :func:`~kqcircuits.simulations.export.sonnet.sonnet_export.export_sonnet`.

The export function takes a list of simulation objects as an argument, where each simulation object corresponds
to a unique simulation.
The export functions also take several tool-specific parameters to setup the simulations.

The output from the KQCircuits simulation export is a stand-alone folder consisting of scripts and data files needed to
execute the simulations within the external simulation tool.
The stand-alone folder can be copied to an external environment in which KQCircuits does not need to be installed.
Automated scripting can handle the simulations from building up the geometry until post-processing of the simulation
results.

More detailed guidance for the simulations is given below:

.. toctree::
    :glob:

    simulation/simulation_objects
    simulation/simulation_scripts
    simulation/simulation_features
    simulation/gmsh_elmer_export
    simulation/export_and_run
    simulation/elmer_remote_workflow