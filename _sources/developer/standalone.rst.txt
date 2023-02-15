.. _standalone:

KLayout Standalone Usage
========================

The :ref:`developer_setup` or :ref:`salt_package` sections described setting up KQCircuits for use
with KLayout Editor (GUI). However, KQC can also be used without KLayout
Editor by using the standalone KLayout Python module. This lets you develop
and use KQCircuits completely within any Python development environment of
your choice, without running KLayout GUI. For example, any debugger can then
be used and automated tests can be performed. The KQCircuits elements can
also be visualized using any suitable viewer or library during development.

Prerequisites
-------------

If you want to run KQCircuits outside of the KLayout Editor, you will need
Python 3 and ``pip`` installed.

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

    python -m pip install -e klayout_package/python

The previous command installs only the packages which are always required
when using KQC. Other packages may be required for specific purposes, and
these can be installed by using instead a command like::

    python -m pip install -e "klayout_package/python[docs,tests,notebooks]"

You can choose for which purposes you want to install the requirements by
modifying the text in the square brackets. Note that there should not be any
spaces within the brackets.

The required packages are defined in :git_url:`setup.py <klayout_package/python/setup.py>` (in KQCircuits `python` directory), so
if there are problems with some specific package, you may try modifying it or
install those packages manually.

Usage
-----

The independence from KLayout GUI makes it possible to do all development of
KQCircuits fully within a Python IDE of your choice. For example, standalone
debuggers and automated testing (see :ref:`testing`) can be done, which would
not be possible without the standalone KLayout module.

The preferred way to instantiate a drawing environment in standalone mode is with the :class:`.KLayoutView` object::

    from kqcircuits.klayout_view import KLayoutView
    view = KLayoutView()

This creates the required object structure and has helper methods for inserting cells and exporting images. See the
:class:`.KLayoutView` API documentation for more details.

  .. note::
    The user **must** keep a reference to the :class:`.KLayoutView` instance in scope, as long as references to the layout or
    individual cells are used.

Jupyter notebook usage
----------------------

There is an example Jupyter notebook :git_url:`viewer.ipynb <notebooks/viewer.ipynb>` in the notebooks
folder, which shows how to create and visualize KQCircuits elements with the
standalone KLayout module. Run it like::

    jupyter-notebook notebooks/viewer.ipynb

Any other files in the notebooks folder will be ignored by git, so you can
create your own notebooks based on :git_url:`viewer.ipynb <notebooks/viewer.ipynb>` in that folder. This
notebook requires that ``notebooks`` was specified as a feature during
installation.
