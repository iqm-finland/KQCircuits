.. _standalone:

Developer Standalone module Setup
=================================

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

- Python 3.10.14, 3.11.2

Older versions of klayout (<0.28) do not support certain new features of
KQCircuits. If you want to use older klayout you may need to check out a
suitable older version of KQCircuits too. API changes of klayout are backwards
compatible so you are safe using older KQCircuits versions with the latest
KLayout.

Installation
-------------

We recommend setting up a Python virtual environment, `"venv" <https://docs.python.org/3/library/venv.html>`__.
This helps with containing the set of dependencies, not letting them interfere with other environments in your system.

If you have not yet done so, ``git clone`` the KQCircuits source code from
https://github.com/iqm-finland/KQCircuits to a location of your choice.
Same cloned local repository used for GUI developer installation (:ref:`developer_setup`)
can be used for standalone installation.

Consider one of three types of installation.

1. Basic installation
^^^^^^^^^^^^^^^^^^^^^

Activate your virtual environment (if you have one) and write in command prompt /
terminal:

.. code-block:: console

    python -m pip install -e klayout_package/python

The previous command installs only the packages which are always required
when using KQC. Other packages may be required for specific purposes,
see :ref:`dependency_extensions`. A command that installs every dependency is:

.. code-block:: console

    python -m pip install -e "klayout_package/python[docs,tests,notebooks,simulations,graphs]"

You can choose for which purposes you want to install the requirements by
modifying the text in the square brackets. Note that there should not be any
spaces within the brackets.

2. Reproducible, Secure Installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For improved security, the dependencies can be installed such that every version
of every dependency package is controlled and their hashes generated and validated.
We host trusted dependency versions at :git_url:`klayout_package/python/requirements`.
If installed that way, it is also easier to troubleshoot problems since the environment will be identical
to the one main developers of KQCircuits have.

Install minimum requirements of KQCircuits, subsituting ``<platform>`` with ``win``, ``mac`` or ``linux``:

.. code-block:: console

    cd klayout_package/python
    python -m pip install -r requirements/<platform>/requirements.txt
    python -m pip install --no-deps -e .

You can afterwards install other requirements needed for specific purposes (in this case doc and test):

.. code-block:: console

    python -m pip install -r requirements/<platform>/doc-requirements.txt -r requirements/<platform>/test-requirements.txt

See :git_url:`klayout_package/python/requirements` and :ref:`dependency_extensions` for full list of requirements files.

3. KQCircuits exclusive python environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have ``pip-tools`` installed, you can use the ``pip-sync`` command to completely rewrite you python environment
to only use the pinned KQCircuits requirements, removing other packages.
Only do this kind of installation on a virtual environment specifically created for using KQCircuits.

.. code-block:: console

    cd klayout_package/python
    python -m pip install -r requirements/<platform>/pip-requirements.txt
    pip-sync requirements/<platform>/requirements.txt requirements/<platform>/test-requirements.txt
    python -m pip install --no-deps -e .

We first install requirements needed for ``pip-sync`` command compiled in the ``pip-requirements.txt`` file,
then we run the actual ``pip-sync`` command. Since ``pip-sync`` will completely wipe out your virtual environment,
you will need to know in advance which dependency extensions you will need and list them within the single ``pip-sync``
command.

.. _dependency_extensions:

Dependency extensions
^^^^^^^^^^^^^^^^^^^^^

We divided dependencies used by KQCircuits into following categories:

- ``requirements.txt``: Dependencies needed to use core KQCircuits API
- ``tests``, ``test-requirements.txt``: Dependencies needed to run unit tests (see :ref:`testing`) and linter. Recommended for developers of KQCircuits code.
- ``docs``, ``doc-requirements.txt``: Dependencies needed to generate KQCircuits documentation, see :ref:`documentation`.
- ``simulations``, ``sim-requirements.txt``: Dependencies needed to export and run simulations, see :ref:`export_and_run`.
- ``notebooks``, ``notebook-reqruiements.txt``: Dependencies needed to run Jupyter notebooks for demonstrations or for calculating needed designs.
- ``graphs``, ``graph-reqruiements.txt``: Dependencies needed to visualise graphs, for example :git_url:`util/netlist_as_graph.py`.
- ``pip-requirements.txt``: Dependencies needed for ``pip-tools``.

PyPI Installation
^^^^^^^^^^^^^^^^^

KQCircuits is also publicly available in the PyPI index and can be installed using:

.. code-block:: console

    pip install kqcircuits

You won't be able to easily modify KQCircuits code and you won't have access to many features such as
scripts, masks, documentation and notebooks.
A new Python package is automatically uploaded to PyPI for every tagged commit in GitHub.

Usage
-----

The independence from KLayout GUI makes it possible to do all development of
KQCircuits fully within a Python IDE of your choice. For example, standalone
debuggers and automated testing (see :ref:`testing`) can be done, which would
not be possible without the standalone KLayout module.

It is possible to generate masks, run simulation scripts or even the actual simulations on the
command line:

.. code-block:: console

    kqc mask quick_demo.py
    python klayout_package/python/scripts/simulations/double_pads_sim.py -q
    kqc sim waveguides_sim_compare.py -q

The output of the above commands will be in the automatically created ``tmp`` directory. If you
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
standalone KLayout module. Run it like:

.. code-block:: console

    jupyter-notebook notebooks/viewer.ipynb


Updating the required dependencies
----------------------------------

Don't do it unless absolutely necessary! The security model (TOFU) works best if
dependencies are rarely changed. When updating dependencies try to verify that
the new versions are legitimate.

Edit the ``*requirements.in`` files according to your needs. Try to keep >=, <=
and == version constraints to a minimum. Try to improve other dependencies too,
not only the ones your need.

Compile the new ``requirements/<platform>/*requirements.txt`` files for
every source ``*requirements.in`` file you changed (make sure you have ``pip-tools`` installed):

.. code-block:: console

    cd klayout_package/python
    pip-compile --allow-unsafe --generate-hashes --upgrade --output-file=requirements/<platform>/requirements.txt requirements.in
    pip-compile --allow-unsafe --generate-hashes --upgrade --output-file=requirements/<platform>/doc-requirements.txt doc-requirements.in
    [...]

Substitute ``<platform>`` with ``win``, ``mac`` or ``linux``, and please make sure that
the files will get compiled for other platforms too, not just the one you are using.

Some requirements files don't have their corresponding ``*reqruirements.in`` source file.
One such file is ``requirements/<platform>/pip-requirements.txt``, which compiles requirements of ``pip-tool``
for each platform. Other requirements files are only used for CI operations.
