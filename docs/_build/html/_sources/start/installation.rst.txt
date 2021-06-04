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

- Linux (Ubuntu 18.04/20.04 LTS, 64-bit): KLayout 0.26.4, 0.26.7 - 0.26.12
- MacOS: KLayout 0.26.3, 0.26.12 (recommended version `HomeBrew-Python3 included`)
- Windows 10 (64-bit): KLayout 0.26.3, 0.26.4, 0.26.7 - 0.26.9, 0.26.11, 0.26.12

Basic automatic installation
----------------------------

Select "Tools -> Manage Packages" to install the KQCircuits package:

.. image:: ../images/install.gif

Note that KLayout was started in edit mode, see :ref:`usage`.

Developers should rather check out the source code and run KQCircuits from
there, see the :ref:`developer_setup`.
