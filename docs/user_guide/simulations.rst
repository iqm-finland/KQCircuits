External simulation tools
====================================

KQCircuits supports exports to following external simulation tools:

* `Ansys HFSS <https://www.ansys.com/products/electronics/ansys-hfss>`_ and `Q3D Extractor <https://www.ansys.com/products/electronics/ansys-q3d-extractor>`_
* `Sonnet <https://www.sonnetsoftware.com>`_
* `Gmsh <https://gmsh.info>`_ and `Elmer <http://www.elmerfem.org>`_


Creating simulation object
--------------------------

Simulation export begins by creating an instance of ``Simulation`` class. The simulation object includes following information:

* name (defines export filenames)
* geometry for the simulation
* port locations and types

Geometry from Klayout GUI
^^^^^^^^^^^^^^^^^^^^^^^^^

When you have an active project open, import the following and get the top cell::

    from kqcircuits.klayout_view import KLayoutView
    from kqcircuits.simulations.simulation import Simulation

    top_cell = KLayoutView.get_active_cell()

Create an instance of ``Simulation``::

    simulation = Simulation.from_cell(top_cell, name='Dev', margin=100)

The ``simulation`` object is needed for Ansys export and Sonnet export (more details in following sections). Alternatively, run following macros in Klayout:

* `scripts/macros/export/export_ansys.lym <https://github.com/iqm-finland/KQCircuits/blob/main/klayout_package/python/scripts/macros/export/export_ansys.lym>`_
* `scripts/macros/export/export_sonnet.lym <https://github.com/iqm-finland/KQCircuits/blob/main/klayout_package/python/scripts/macros/export/export_sonnet.lym>`_

Geometry from KQCircuits library
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Define the geometry and ports in KQCircuits by inheriting ``Simulation`` class. Following creates waveguide crossing the domain box::

    from kqcircuits.simulations.simulation import Simulation
    from kqcircuits.pya_resolver import pya
    import sys
    import logging
    from kqcircuits.util.export_helper import get_active_or_new_layout

    class WaveguideSimulation(Simulation):
        def build(self):
            self.produce_waveguide_to_port(pya.DPoint(self.box.left, self.box.center().y),
                                           pya.DPoint(self.box.right, self.box.center().y),
                                           1, 'right', use_internal_ports=False)


Get layout for ``Simulation`` object::

    logging.basicConfig(level=logging.WARN, stream=sys.stdout)
    layout = get_active_or_new_layout()

Create an instance of ``Simulation``::

    simulation = WaveguideSimulation(layout, name='Dev', box=pya.DBox(pya.DPoint(0, 0), pya.DPoint(500, 500)))

``Simulation`` class and it's subclasses are located in folder `kqcircuits/simulations/ <https://github.com/iqm-finland/KQCircuits/tree/main/klayout_package/python/kqcircuits/simulations>`_.

Ansys export
------------

Once the ``simulation`` object is created, call function ``export_ansys_json`` to export the geometry as GDSII file and meta-data in json format. Parameter ``ansys_tool`` determines whether to use HFSS ('hfss') or Q3D Extractor ('q3d')::

    from kqcircuits.simulations.export.ansys.ansys_export import export_ansys_json, copy_ansys_scripts_to_directory, export_ansys_bat, export_ansys
    path = "C:\\Your\\Path\\Here\\"
    json = export_ansys_json(simulation, path, ansys_tool='hfss')

Performing simulations requires Ansys-scripts, which are located at `scripts/simulations/ansys/ <https://github.com/iqm-finland/KQCircuits/tree/main/klayout_package/python/scripts/simulations/ansys>`_. Usually, it's convenient to copy this folder to the export path by calling ``copy_ansys_scripts_to_directory``::

    copy_ansys_scripts_to_directory(path)

You can create a Windows batch file for running multiple simulations in a row by calling function ``export_ansys_bat``. The first argument is a list of exported json filenames::

    bat = export_ansys_bat([json], path)

Alternatively, you can call ``export_ansys`` to cover last three steps. This exports multiple simulations that are stored in a list, copies the Ansys-scripts into the folder, and creates the Windows batch file::

    bat = export_ansys([simulation], path, ansys_tool='hfss')

Ansys scripts
^^^^^^^^^^^^^

The folder `scripts/simulations/ansys/ <https://github.com/iqm-finland/KQCircuits/tree/main/klayout_package/python/scripts/simulations/ansys>`_ contains several IronPython scripts to run simulations in Ansys Electronics Desktop. Scripts support HFSS and Q3D Extractor frameworks.

The scripts are developed and tested with Ansys Electronic Desktop 2021 R1 on Windows x64.


The primary use case is to estimate capacitive couplings between different elements in the layout, where each element
of interest has a port in the simulation. The capacitances are represented as a matrix, where the *Cij* is the
capacitance between two ports *i* and *j*, and *Cii* is the capacitance between port *i* and ground.

Main scripts:
"""""""""""""

* `import_simulation_geometry.py <https://github.com/iqm-finland/KQCircuits/blob/main/klayout_package/python/scripts/simulations/ansys/import_simulation_geometry.py>`_

  Argument: path to json file exported by ``export_ansys_json``.

  Creates a new project, imports the geometry, defines ports/nets and materials, and sets up the analysis setup.

* `create_capacitive_pi_model.py <https://github.com/iqm-finland/KQCircuits/blob/main/klayout_package/python/scripts/simulations/ansys/create_capacitive_pi_model.py>`_

  No argument.

  Adds solution variables and reports for a PI model between all ports/nets in the current design.

  The variables ``yy_i_j`` give the scalar admittance between port ``i`` and ``j``, or the admittance from port ``i`` to
  ground if ``i==j``. The ``yy``-variables are created only in HFSS.

  Similarly, the variables ``C_i_j`` give the capacitance between ports and from ports to ground,
  assuming a purely capacitive model. This assumption is valid as long as the resulting ``C_i_j`` are constant over frequency.

* `export_solution_data.py <https://github.com/iqm-finland/KQCircuits/blob/main/klayout_package/python/scripts/simulations/ansys/export_solution_data.py>`_

  No argument.

  Exports data from the solutions. *projectname_CMatrix.txt* contains the elements ``C_i_j`` in fF (at 1 GHz in HFSS).
  *projectname_results.json* contains all ``C_i_j`` and ``yy_i_j`` elements for all frequencies in the solution.
  In case of HFSS, *projectname_SMatrix.s2p* contains the S-parameters.

* `import_and_simulate.py <https://github.com/iqm-finland/KQCircuits/blob/main/klayout_package/python/scripts/simulations/ansys/import_and_simulate.py>`_

  Argument: path to json file exported by ``export_ansys_json``.

  Performs the full simulation sequence including running the three other scripts, saving the project, and running the simulation.


Additional scripts for use cases other than capacitive coupling exist.
These are enabled in `import_and_simulate.py <https://github.com/iqm-finland/KQCircuits/blob/main/klayout_package/python/scripts/simulations/ansys/import_and_simulate.py>`_ with a list of strings as parameters to ``export_ansys``,
e.g., to enable exporting Time Domain Reflectometry (TDR) and non-de-embedded Touchstone (``.sNp``) files::

    export_ansys(..., export_processing=['tdr', 'snp_no_deembed'])

The optional scripts are listed below.

Optional scripts:
"""""""""""""""""

* `export_snp_no_deembed.py <https://github.com/iqm-finland/KQCircuits/blob/main/klayout_package/python/scripts/simulations/ansys/export_snp_no_deembed.py>`_

  No argument.

  Disables de-embedding and exports the :math:`S`-matrix network data to a Touchstone (``.sNp``) file.

  Works only in HFSS.

* `export_tdr.py <https://github.com/iqm-finland/KQCircuits/blob/main/klayout_package/python/scripts/simulations/ansys/export_tdr.py>`_

  No argument.

  Creates a Time Domain Reflectometry report using ``TDRZt(port)`` for all ports and exports the data to a ``.csv``.

  Works only in HFSS.


Sonnet export
-------------

Once the ``simulation`` object is created, call function ``export_sonnet_son`` to export simulation into ``.son`` file::

    from kqcircuits.simulations.export.sonnet.sonnet_export import export_sonnet_son, export_sonnet
    path = "C:\\Your\\Path\\Here\\"
    son = export_sonnet_son(simulation, path)

Multiple simulations can be exported by calling ``export_sonnet``. The function takes list of simulations as it's first parameter::

    sons = export_sonnet([simulation], path)

Gmsh/Elmer export
-----------------

Usage of Gmsh and Elmer export is similar to Ansys export.
The ``simulation`` object can be used with function ``export_elmer`` to export all necessary files to produce Gmsh/Elmer
simulations.

There is an example at 'klayout_package/python/scripts/simulations/waveguides_sim_compare.py', which creates a simulation folder
with simulation scripts. The folder is created to `$TMP` (usually `kqcircuits/tmp`). The contents of the folder is something like::

    waveguides_sim_elmer
    ├── COMMIT_REFERENCE
    ├── scripts
    │   ├── elmer_helpers.py
    │   ├── gmsh_helpers.py
    │   └── run.py
    ├── sif
    │   ├── CapacitanceMatrix.sif
    │   └── electric_potential.pvsm
    ├── simulation.oas
    ├── simulation.sh
    ├── waveguides_n_guides_1.gds
    ├── waveguides_n_guides_1.json
    ├── waveguides_n_guides_1.sh
    ├── waveguides_n_guides_2.gds
    ├── waveguides_n_guides_2.json
    └── waveguides_n_guides_2.sh

`script` folder contains scripts that are used for preparing the simulations.

`sif` contains the Solver Input Files (SIF) for Elmer (scripts in `scripts` -folder are used 
to build the SIF files for each simulation).

`waveguides_n_guides_1.sh`, `waveguides_n_guides_2.sh`, `...` are the shell scripts for running each simulation.
Each script executes Gmsh (mesh creation), computes the FEM model using Elmer (computes the 
capacitance matrix), and visualizes the results using Paraview.

`simulation.sh` is a shell script for running all simulations at once.
The simulations are executed by running the `.sh` file in the output folder (here `waveguides_sim_elmer`).

Please note that running the example requires the installation of

* gmsh python api
  ``pip install gmsh``
* Elmerfem solver
  see https://github.com/ElmerCSC/elmerfem
* Paraview
  https://www.paraview.org/

Gmsh api suffices if one needs to generate the mesh only.


