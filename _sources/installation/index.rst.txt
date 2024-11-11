.. _installation:

Installation
============

There are three distinct ways of installing KQCircuits suitable for different use cases.

The simplest way is installing the latest KQCircuits Salt Package with KLayout's package manager.
This gives the user instant access to KQCircuits from KLayout GUI but in a slightly limited read-only way. See
:ref:`salt_package`.

Developers should rather install git, clone the source code of KQCircuits and link it to the KLayout application.
See the :ref:`developer_setup`. This way the KQCircuits extension in the KLayout GUI application
will use the exact codebase present in the cloned, version-controlled local repository.

For GUI-less features developers should also install KQCircuits as a standalone KLayout Python module, for that see
:ref:`standalone`. This allows developers to make use of KQCircuits features in their own
python code by importing the ``kqcircuits`` module. This also enables terminal commands such as::

  kqc sim <simulation_script> # to export simulation data and then to process it with a third-party simulator
  kqc mask <mask_script>      # to export mask layout files for fabrication

.. toctree::
   :maxdepth: 1

   klayout
   known_issues
