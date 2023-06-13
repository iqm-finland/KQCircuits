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

Older versions of klayout (<0.28) do not support certain new features of
KQCircuits. If you want to use older klayout you may need to check out a
suitable older version of KQCircuits too. API changes of klayout are backwards
compatible so you are safe using older KQCircuits versions with the latest
KLayout.

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

    python -m pip install -e "klayout_package/python[docs,tests,notebooks,simulations]"

You can choose for which purposes you want to install the requirements by
modifying the text in the square brackets. Note that there should not be any
spaces within the brackets.

PyPI Installation
^^^^^^^^^^^^^^^^^

If you do not need all KQCircuits sources but only the core KQC classes you may simply run ``pip
install kqcircuits`` to get the Python package only. You can use this the same way as the full
developer installation but remember that scripts, masks, documentation and notebooks are not part of
the Python package. A new Python package is automatically uploaded to PyPI for every tagged commit
in GitHub.

The ``kqcircuits`` Python package may be used with an independently downloaded KQCircuits source
directory to run tests, simulation scripts or build documentation or masks from there. You are
supposed to run most of these from the source directory or you may need to specify the
``KQC_ROOT_PATH`` environment variable so that ``kqcircuits`` finds the sources.

Usage
-----

The independence from KLayout GUI makes it possible to do all development of
KQCircuits fully within a Python IDE of your choice. For example, standalone
debuggers and automated testing (see :ref:`testing`) can be done, which would
not be possible without the standalone KLayout module.

It is possible to generate masks, run simulation scripts or even the actual simulations on the
command line::

    python klayout_package/python/scripts/masks/quick_demo.py
    python klayout_package/python/scripts/simulations/double_pads_sim.py -q
    kqc simulate waveguides_sim_compare.py -q

The output of the above commands will be in the automaticaly created ``tmp`` directory. If you
desire the outputs elsewhere set the ``KQC_TMP_PATH`` environment variable to some other path.

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

There is an example Jupyter notebook `KQCircuits-Examples/notebooks/viewer.ipynb <https://github.com/iqm-finland/KQCircuits-Examples/blob/main/notebooks/viewer.ipynb>`__ in the notebooks
folder, which shows how to create and visualize KQCircuits elements with the
standalone KLayout module. Run it like::

    jupyter-notebook notebooks/viewer.ipynb
