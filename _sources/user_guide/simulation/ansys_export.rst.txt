Ansys export
------------

Once the ``simulation`` object is created, call function ``export_ansys_json`` to export the geometry as GDSII file and meta-data in json format. Parameter ``ansys_tool`` determines whether to use HFSS ('hfss') or Q3D Extractor ('q3d').
HFSS eigenmode simulations are done with 'eigenmode', this is used for :ref:`py-epr` as well::

    from kqcircuits.simulations.export.ansys.ansys_export import export_ansys_json, copy_ansys_scripts_to_directory, export_ansys_bat, export_ansys
    path = "C:\\Your\\Path\\Here\\"
    json = export_ansys_json(simulation, path, ansys_tool='hfss')

Performing simulations requires Ansys-scripts, which are located at :git_url:`scripts/simulations/ansys/ <klayout_package/python/scripts/simulations/ansys>`. Usually, it's convenient to copy this folder to the export path by calling ``copy_ansys_scripts_to_directory``::

    copy_ansys_scripts_to_directory(path)

You can create a Windows batch file for running multiple simulations in a row by calling function ``export_ansys_bat``. The first argument is a list of exported json filenames::

    bat = export_ansys_bat([json], path)

Alternatively, you can call ``export_ansys`` to cover last three steps. This exports multiple simulations that are stored in a list, copies the Ansys-scripts into the folder, and creates the Windows batch file::

    bat = export_ansys([simulation], path, ansys_tool='hfss')

Ansys scripts
^^^^^^^^^^^^^

The folder :git_url:`scripts/simulations/ansys/ <klayout_package/python/scripts/simulations/ansys>` contains several IronPython scripts to run simulations in Ansys Electronics Desktop. Scripts support HFSS and Q3D Extractor frameworks.

The scripts are developed and tested with Ansys Electronic Desktop 2021 R1 on Windows x64.


The primary use case is to estimate capacitive couplings between different elements in the layout, where each element
of interest has a port in the simulation. The capacitances are represented as a matrix, where the *Cij* is the
capacitance between two ports *i* and *j*, and *Cii* is the capacitance between port *i* and ground.

Main scripts:
"""""""""""""

* :git_url:`import_simulation_geometry.py <klayout_package/python/scripts/simulations/ansys/import_simulation_geometry.py>`

  Argument: path to json file exported by ``export_ansys_json``.

  Creates a new project, imports the geometry, defines ports/nets and materials, and sets up the analysis setup.

* :git_url:`create_capacitive_pi_model.py <klayout_package/python/scripts/simulations/ansys/create_capacitive_pi_model.py>`

  No argument.

  Adds solution variables and reports for a PI model between all ports/nets in the current design.

  The variables ``yy_i_j`` give the scalar admittance between port ``i`` and ``j``, or the admittance from port ``i`` to
  ground if ``i==j``. The ``yy``-variables are created only in HFSS.

  Similarly, the variables ``C_i_j`` give the capacitance between ports and from ports to ground,
  assuming a purely capacitive model. This assumption is valid as long as the resulting ``C_i_j`` are constant over frequency.

* :git_url:`export_solution_data.py <klayout_package/python/scripts/simulations/ansys/export_solution_data.py>`

  No argument.

  Exports data from the solutions. *projectname_CMatrix.txt* contains the elements ``C_i_j`` in fF (at 1 GHz in HFSS).
  *projectname_results.json* contains all ``C_i_j`` and ``yy_i_j`` elements for all frequencies in the solution.
  In case of HFSS, *projectname_SMatrix.s2p* contains the S-parameters.

* :git_url:`import_and_simulate.py <klayout_package/python/scripts/simulations/ansys/import_and_simulate.py>`

  Argument: path to json file exported by ``export_ansys_json``.

  Performs the full simulation sequence including running the three other scripts, saving the project, and running the simulation.


Additional scripts for use cases other than capacitive coupling exist.
These are enabled in :git_url:`import_and_simulate.py <klayout_package/python/scripts/simulations/ansys/import_and_simulate.py>` with a list of strings as parameters to ``export_ansys``,
e.g., to enable exporting Time Domain Reflectometry (TDR) and non-de-embedded Touchstone (``.sNp``) files::

    export_ansys(..., simulation_flags=['tdr', 'snp_no_deembed'])

The optional scripts are listed below.

Optional scripts:
"""""""""""""""""

* :git_url:`export_snp_no_deembed.py <klayout_package/python/scripts/simulations/ansys/export_snp_no_deembed.py>`

  No argument.

  Disables de-embedding and exports the :math:`S`-matrix network data to a Touchstone (``.sNp``) file.

  Works only in HFSS.

* :git_url:`export_tdr.py <klayout_package/python/scripts/simulations/ansys/export_tdr.py>`

  No argument.

  Creates a Time Domain Reflectometry report using ``TDRZt(port)`` for all ports and exports the data to a ``.csv``.

  Works only in HFSS.



.. _py-epr:

pyEPR
"""""

`pyEPR <https://github.com/zlatko-minev/pyEPR>`_ is supported for HFSS eigenmode simulations.
A simulation needs to be created with ``ansys_tool=eigenmode`` and ``simulation_flags=['pyepr']``.
An example simulation is found at :git_url:`klayout_package/python/scripts/simulations/xmons_direct_coupling_pyepr.py`.
See ``notebooks\pyEPR_example.ipynb`` for an example on using pyEPR itself.
