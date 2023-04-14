Simulation export settings
==========================

The settings depend highly on the employed tool, but some settings are universal. These are primarily given to the :class:`.Simulation` class as PCell parameters in contrast to export functions corresponding to different programs. Please refer to the docstrings and implementations for details:

   * :func:`~kqcircuits.simulations.export.ansys.ansys_export.export_ansys`
   * :func:`~kqcircuits.simulations.export.elmer.elmer_export.export_elmer`
   * :func:`~kqcircuits.simulations.export.sonnet.sonnet_export.export_sonnet`

Elmer export, on the other hand, has some details explained in :ref:`gmsh_elmer_export`.