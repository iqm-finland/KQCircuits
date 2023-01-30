.. _getting_started:

Installation
============

There are three distinct ways of installing KQCircuits suitable for different use cases.

The simplest way is installing the latest KQCircuits Salt Package with KLayout's package manager.
This gives the user instant access to KQCircuits but in a slightly limited read-only way. See
:ref:`salt_package`.

Developers should rather install git, check out the source code and run KQCircuits from there, see
the :ref:`developer_setup`. This is the most powerful and most complex installation method but it
gives full access to everything: creating and modifying chips, running tests and simulations,
building documentation, etc.

It is also possible to use KQCircuits with the standalone KLayout Python module, for that see
:ref:`standalone`.

.. _klayout:

KLayout
-------

Download and install KLayout from https://www.klayout.de/build.html. Builds
should exist there for most common operating systems, choose the correct one
for your OS. Otherwise you need to build KLayout yourself. We will assume in
these instructions, that KLayout has been installed in the default location.

Successfully tested versions:

- Linux (Ubuntu 18.04/20.04 LTS, 64-bit): KLayout 0.26.4, 0.26.7 - 0.28
- MacOS: KLayout 0.26.3, 0.26.12 (recommended version `HomeBrew-Python3 included`)
- Windows 10 (64-bit): KLayout 0.26.3, 0.26.4, 0.26.7 - 0.26.9, 0.26.11, 0.26.12, 0.27.2, 0.27.9, 0.27.13

.. note::
    KQC documetation uses Linux conventions and examples unless explicitly talking about Windows or
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
