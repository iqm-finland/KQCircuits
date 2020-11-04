HFSS simulation scripts
=======================

This folder contains several IronPython scripts needed to run simulations in HFSS of planar structures defined in
KQCircuits.

The primary use case is to estimate capacitive couplings between different elements in the layout, where each element
of interest has a port in the simulation. The capacitances are represented as a matrix, where the *Cij* is the
capacitance between two ports *i* and *j*, and *Cii* is the capacitance between port *i* and ground.

Requirements and assumptions
----------------------------

These scripts were developed and tested with Ansys Electronic Desktop 2020 R1 on Windows x64.

Getting started
---------------

#. Define the geometry and ports in KQCircutis by subclassing ``Simulation``
#. Use ``HfssExport``  to export the geometry as GDSII file and
   meta-data in json format
#. In HFSS, run the script ``import_and_simulate.py``, with the full path to the json file as argument

Steps 2 and 3 can be done in one go by configuring and executing ``notebooks/simulation_runner.py``

Running scripts in HFSS
^^^^^^^^^^^^^^^^^^^^^^^

There are several ways to run a script in HFSS:

#. Through the GUI: Tools > Run Script. There is an extra field *Script Argument* in the bottom of the file picker dialog
   to enter the argument
#. On the command line, \

   ``ansysedt.exe -scriptargs "arguments" -RunScript "script.py"``

   ``ansysedt.exe -scriptargs "arguments" -RunScriptAndExit "script.py"``
#. Through the Python console in HFSS or inside another script,

   ``oDesktop.RunScriptWithArguments(script, argument)``

   ``oDesktop.RunScript(script)``
#. Invoking the IronPython kernel directly; this has not been tested yet.

Available scripts
-----------------
* ``import_simulation_geometry.py``

  Argument: path to json file exported by ``HfssExport``.

  Creates a new project, imports the geometry, defines ports and materials, and sets up the

* ``create_capacitive_pi_model.py``

  No argument.

  Adds solution variables and reports for a PI model between all ports in the current design.

  The variables ``yy_i_j`` give the scalar admittance between port ``i`` and ``j``, or the admittance from port ``i`` to
  ground if ``i==j``.

  Similarly, the variables ``C_i_j`` give the capacitance between ports and from ports to ground,
  assuming a purely capacitive model. This assumption is valid as long as the resulting ``C_i_j`` are constant over frequency.

* ``export_capacitive_pi_model.py``

  No argument.

  Exports data from the capacitive pi model. *projectname_CMatrix.txt* contains the elements ``C_i_j`` in fF at 1 GHz.
  *projectname_results.json* contains all ``C_i_j`` and ``yy_i_j`` elements for all frequencies in the solution.

* ``import_and_simulate.py``

  Argument: path to json file exported by ``HfssExport``.

  Performs the full simulation sequence including running the three other scripts, saving the project, and running the simulation.


Copyright
---------

Copyright (c) 2019-2020 IQM Finland Oy.

All rights reserved. Confidential and proprietary.

Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy's prior written permission.
