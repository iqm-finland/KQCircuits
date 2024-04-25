.. _getting_started:

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

.. _klayout:

KLayout
-------

Download and install KLayout from https://www.klayout.de/build.html. Builds
should exist there for most common operating systems, choose the correct one
for your OS. Otherwise you need to build KLayout yourself. We will assume in
these instructions, that KLayout has been installed in the default location.

KLayout is an actively maintained project with regular feature updates, bugfixes and
stability improvements. We recommend using the latest version. KQCircuits is automatically
tested using KLayout versions:

- 0.27.13
- 0.28.17
- latest version of 0.29

on the following platforms:

- Linux: Ubuntu 22.04 LTS, 64-bit
- MacOS: latest github image
- Microsoft Windows Server 2022, OS version 10

.. note::
    KQC documentation uses Linux conventions and examples unless explicitly talking about Windows or
    MacOS. For example a Windows user should mentally translate path separator ``/`` to ``\``,
    klayout executable ``klayout`` to ``%APPDATA%\KLayout\klayout_app.exe`` or the KLayout
    environment directory ``~/.klayout`` to ``%HOMEPATH%\KLayout``.

.. _installation_issues:

Known installation issues
-------------------------

For some specific KLayout builds there can be problems with KQCircuits
installation that require some extra steps:

* For some macOS BigSur KLayout builds (at least for KLayout v0.27.x), KQC
  might not work due to a problem with the KLayout included ``setuptools``
  package. The KQC libraries will not be visible and one might see the error
  message ``"No module named '_distutils_hack'"`` when trying to run macros.
  This can be fixed by installing manually the ``setuptools`` package into
  KLayout (at least ``setuptools`` v52.0.0 and v57.4.0 should work, probably
  also some other versions). See
  :ref:`manual_installation_of_klayout_packages` for instructions on how to
  install a specific package version to KLayout.

.. _manual_installation_of_klayout_packages:

Installing different Python package versions to KLayout manually
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes there are issues with specific package versions in the KLayout
Python environment. To install a different version of some package, use:

    ``pip install <PACKAGE>==<VERSION> --target=<KLAYOUT-PACKAGE-DIR>``

The KLAYOUT-PACKAGE-DIR should be the path to the site-packages directory
used by KLayout. If you don't know where that is, you can find it by opening
the KLayout macro editor and writing ``import pip`` and then ``pip.__path__``
in the console.

Notice that this only affects the GUI installation of KQCircuits.
The standalone, GUI-less KQCircuits installation will use whatever Python environment
where it was explicitly installed in, which is most likely separate from the Python
environment used by KLayout.
