.. _standalone:

Setup with KLayout standalone Python module
===========================================

The :ref:`getting_started` section described setting up KQCircuits for use
with KLayout Editor (GUI). However, KQC can also be used without KLayout
Editor by using the standalone KLayout Python module. This lets you develop
and use KQCircuits completely within any Python development environment of
your choice, without running KLayout GUI. For example, any debugger can then
be used and automated tests can be performed. The KQCircuits elements can
also be visualized using any suitable viewer or library during development.

Prerequisites
-------------

If you want to run KQCircuits outside of the KLayout Editor, you will need
a Python 3 installation. The installation also requires `pip`.

Successfully tested with

- Python 3.7.6, 3.8.5

Installation
-------------

If you have not yet done so, ``git clone`` the KQCircuits source code from
https://github.com/iqm-finland/KQCircuits to a location of your choice.

This section explains how to install KQC in "development mode", so that a
link to your local KQC repo is added to the python environment. When using
KQC installed in this way, the version in your local repo is thus used.

To do this, activate your python environment and write in command prompt /
terminal::

    python -m pip install -e .

The previous command installs only the packages which are always required
when using KQC. Other packages may be required for specific purposes, and
these can be installed by using instead a command like::

    python -m pip install -e .[docs,tests,gds_export,png_export]

You can choose for which purposes you want to install the requirements by
modifying the text in the square brackets. Note that there should not be any
spaces within the brackets.

The required packages are defined in ``setup.py`` (in KQC root directory), so
if there are problems with some specific package, you may try modifying it or
install those packages manually.

Usage
-----

The independence from KLayout GUI makes it possible to do all development of
KQCircuits fully within a Python IDE of your choice. For example, standalone
debuggers and automated testing (see :ref:`testing`) can be done, which would
not be possible without the standalone KLayout module.
