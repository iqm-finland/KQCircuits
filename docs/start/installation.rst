Installation
============

.. _klayout:

KLayout
-------

Download and install KLayout from https://www.klayout.de/build.html. Builds
should exist there for most common operating systems, choose the correct one
for your OS. Otherwise you need to build KLayout yourself. We will assume in
these instructions, that KLayout has been installed in the default location.

Successfully tested versions:

- Linux (Ubuntu 18.04/20.04 LTS, 64-bit): KLayout 0.26.4, 0.26.7 - 0.27.2
- MacOS: KLayout 0.26.3, 0.26.12 (recommended version `HomeBrew-Python3 included`)
- Windows 10 (64-bit): KLayout 0.26.3, 0.26.4, 0.26.7 - 0.26.9, 0.26.11, 0.26.12, 0.27.2

Basic automatic installation
----------------------------

Select "Tools -> Manage Packages" to install the KQCircuits package:

.. image:: ../images/install.gif

Note that KLayout was started in edit mode, see :ref:`usage`.

Developers should rather check out the source code and run KQCircuits from
there, see the :ref:`developer_setup`.

.. note::
   If KQCircuits is not working properly after installation (KQC libraries
   not visible, running any macro gives an error, etc.), there might be some
   problem with the specific KLayout version/build you are using, see
   :ref:`installation_issues` section for possible solutions.

Upgrading Salt Package
----------------------

After upgrading KQCircuits package KLayout needs to be restarted. See the release notes
for further details.

Downgrading or upgrading several steps at once is not guaranteed to always work. Upgrading KQC
usually works but the safest approach is to uninstall KQC and then install a new version.

Release Notes
-------------

Here we list particular quirks of specific KQCircuits Salt packages. For a full list of changes see
the code repository.

* Version 4.1.0 requires full reinstall of KQC. Qubits directory has moved, to remove the earlier
  version we need to first remove KQC then install the new version.
* Version 4.0.0 requires full reinstall of KQC. Several files have been relocated, without a full
  reinstall multiple versions of the same file will be left behind.
* Version 3.3.0 needs manual install of ``tqdm`` Python module.

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
Python environment. To install a different version of some package, use::

    pip install <PACKAGE>==<VERSION> --target=<KLAYOUT-PACKAGE-DIR>

The KLAYOUT-PACKAGE-DIR should be the path to the site-packages directory
used by KLayout. If you don't know where that is, you can find it by opening
the KLayout macro editor and writing ``import pip`` and then ``pip.__path__``
in the console.
