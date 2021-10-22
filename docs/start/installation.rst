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
