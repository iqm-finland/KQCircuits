Export functions
================

The export functions take the list of simulation objects, the simulation folder path, and several tool-specific
arguments to produce files and scripts to run simulations in an external simulation software.
For the details of the tool-specific arguments, please see the API of each function:

   * :func:`~kqcircuits.simulations.export.ansys.ansys_export.export_ansys`,
   * :func:`~kqcircuits.simulations.export.elmer.elmer_export.export_elmer`,
   * :func:`~kqcircuits.simulations.export.sonnet.sonnet_export.export_sonnet`.

Ansys export
^^^^^^^^^^^^

Before exporting the Ansys simulations make sure that the ``ANSYS_EXECUTABLE`` parameter in
:git_url:`kqcircuits/defaults.py <klayout_package/python/kqcircuits/defaults.py>` matches with your Ansys version and
installation location.
The Ansys simulations are developed and tested with both Windows and Linux installation of the latest
`Ansys Electronics desktop <https://www.ansys.com/products/electronics>`_.


The following example script shows a typical usage of the
:func:`~kqcircuits.simulations.export.ansys.ansys_export.export_ansys` function.
The script generates simulation subclass, creates a simulation object, exports Ansys scripts into a directory, and
finally shows the simulation geometries in Klayout viewer.::

    from kqcircuits.qubits.swissmon import Swissmon
    from kqcircuits.simulations.single_element_simulation import get_single_element_sim_class
    from kqcircuits.util.export_helper import get_active_or_new_layout, create_or_empty_tmp_directory, \
        open_with_klayout_or_default_application
    from kqcircuits.simulations.export.simulation_export import export_simulation_oas
    from kqcircuits.simulations.export.ansys.ansys_export import export_ansys

    sim_class = get_single_element_sim_class(Swissmon)  # Builds a simulation class for Swissmon

    layout = get_active_or_new_layout()
    simulations = [sim_class(layout)]  # Generate the simulation with default parameters

    # Create an empty folder for simulations in KQCircuits/tmp/swissmon_simulation_output
    dir_path = create_or_empty_tmp_directory("swissmon_simulation_output")

    # Export simulations for external simulation software
    export_parameters = {
        'path': dir_path,  # path for the directory is the only mandatory parameter for the export functions
    }
    export_ansys(simulations, **export_parameters)

    # Export the simulation geometries as OAS file and view in Klayout (optional)
    open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))

The above script can be run as a regular python script, or in the KLayout macro editor.
After the execution, the output files are written to a folder in the KQCircuits ``tmp`` directory.

The ``export_ansys`` function produces files and scripts needed to run Ansys simulations.
First, it copies the folders :git_url:`scripts/simulations/ansys/ <klayout_package/python/scripts/simulations/ansys>`
and :git_url:`scripts/simulations/post_process/ <klayout_package/python/scripts/simulations/post_process>` into the simulation
directory.
The first folder contains needed IronPython scripts to run simulations in Ansys Electronics Desktop and the second
includes post processing scripts that can be run after the simulations.
Then it exports x-y-shapes as GDSII file and other meta-data in json format for each simulation.
Finally, it creates a batch file for running all simulations in series.

The simulations can be run by executing the ``simulation.bat`` script file.

More examples of simulation scripts are available in :git_url:`klayout_package/python/scripts/simulations`.

Elmer export
^^^^^^^^^^^^

The Elmer simulations are developed and tested with Linux systems.
Running the simulations requires installation of

* Gmsh python API ``pip install gmsh`` or in secure mode ``pip install -r path/to/sim-requirements.txt``
* Elmerfem solver, see https://github.com/ElmerCSC/elmerfem
* Paraview https://www.paraview.org/

The usage of Elmer simulation export is very similar to Ansys export.
In the above export script, the only change is to replace "ansys" with "elmer" in all occurrence, that is, in these
two lines::

    from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
    export_elmer(simulations, **export_parameters)

Similarly to ``export_ansys``, the ``export_elmer`` copies the Gmsh and Elmer script folder
:git_url:`scripts/simulations/elmer/ <klayout_package/python/scripts/simulations/elmer>` and post-processing
script folder :git_url:`scripts/simulations/post_process/ <klayout_package/python/scripts/simulations/post_process>`
into the simulation directory.
It exports x-y-shapes as GDSII file and other meta-data in json format for each simulation and
creates a script file for running all simulations in series.

The Elmer simulations can be run by executing the ``simulation.sh`` script file.

.. note::
    The ``export_elmer`` and ``export_ansys`` functions take different set of arguments, so the
    ``export_parameters`` must be specified for the functions separately.
    The list of simulations and ``path`` are the only common arguments for all export functions.
    More details of Gmsh and Elmer parameterization and simulations are explained in :ref:`gmsh_elmer_export`.


Sonnet export
-------------

The Sonnet export is incomplete, but there is a possibility to export limited geometries for Sonnet simulations.
Once the simulation objects are created, the function ``export_sonnet`` can be called in very similar manner to
the other export functions.

For example in the above Ansys export script, replace "ansys" with "sonnet" in all occurrence, which is these two
lines::

    from kqcircuits.simulations.export.sonnet.sonnet_export import export_sonnet
    export_sonnet(simulations, **export_parameters)

The ``export_sonnet`` function internally calls function ``export_sonnet_son`` for all simulation objects.
This exports each simulation into a ``.son`` file.
For more information, we refer API for :func:`~kqcircuits.simulations.export.sonnet.sonnet_export.export_sonnet`.

.. _Geometry from KLayout GUI:

Geometry from Klayout GUI
^^^^^^^^^^^^^^^^^^^^^^^^^

An alternative way to export simulations is to draw the geometry (place elements or draw manually) in
KLayout, and run one of the following macros.

* :git_url:`scripts/macros/export/export_ansys.lym <klayout_package/python/scripts/macros/export/export_ansys.lym>`
* :git_url:`scripts/macros/export/export_sonnet.lym <klayout_package/python/scripts/macros/export/export_sonnet.lym>`

Similarly, the simulation instances can be created from an existing KLayout Cell ``cell`` in code::

    simulation = Simulation.from_cell(cell, name='Dev', margin=100)

These methods export the geometry, but do not add any ports to the simulation.
Hence, this can be useful if you want to manually create ports or make other changes for example in Ansys.
