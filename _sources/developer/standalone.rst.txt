.. _standalone:

Developer Standalone module Setup
=================================

The :ref:`developer_setup` or :ref:`salt_package` sections described setting up KQCircuits for use
with KLayout Editor (GUI). However, KQC can also be used **without** KLayout
Editor by using the standalone KLayout Python module. This lets you develop
and use KQCircuits completely within any Python development environment of
your choice, without running KLayout GUI. For example, any debugger can then
be used and automated tests can be performed. The KQCircuits elements can
also be visualized using any suitable viewer or library during development.

Prerequisites
-------------

Make sure you have at least Python 3.11 and ``pip`` installed.
We automatically test that KQCircuits works on latest versions
of following python major releases: ``3.11.x``, ``3.12.x``, ``3.13.x``.
We also test that KQCircuits works on Windows, Ubuntu 24 and MacOS 15.7.3.

Older versions of klayout (<0.28) do not support certain new features of
KQCircuits. If you want to use older klayout you may need to check out a
suitable older version of KQCircuits too. API changes of klayout are backwards
compatible so you are safe using older KQCircuits versions with the latest
KLayout.

Sources
-------

Get KQCircuits' sources (if you haven't already) with:

.. parsed-literal::

    git clone |GIT_CLONE_URL|

Same cloned local repository used for GUI developer installation (:ref:`developer_setup`)
can be used for standalone installation.

Installation
-------------

We recommend setting up a Python virtual environment, `"venv" <https://docs.python.org/3/library/venv.html>`__.
This helps with containing the set of dependencies, not letting them interfere with other environments in your system.
Other virtual environments should work too.

There are many ways to install the KQCircuits library, pick one of the following.

1. Basic installation
^^^^^^^^^^^^^^^^^^^^^

This installation method is quick and simple, but slightly more unpredictable with respect to
the versions of dependent libraries of KQCircuits. It will prioritize installing latest
libraries, which is an untested configuration that may cause some features to break. This method is also
more vulnerable to installing insecure packages.

Activate your virtual environment (if you have one) and write in command prompt /
terminal:

.. code-block:: console

    python -m pip install -e klayout_package/python

This command installs only the minimal set of packages needed to use core features of KQC.
Other packages may be required for specific purposes,
see :ref:`dependency_extensions`. A command that installs every dependency is:

.. code-block:: console

    python -m pip install -e "klayout_package/python[dev,sim]"

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

Install minimum requirements of KQCircuits, subsituting ``<platform>`` with ``win``, ``mac`` or ``linux``.
(If run on WSL terminal, use ``linux``):

.. code-block:: console

    cd klayout_package/python
    python -m pip install -r requirements/<platform>/requirements.txt
    python -m pip install --no-deps -e .

You can afterwards install additional requirements:

.. code-block:: console

    python -m pip install -r requirements/<platform>/dev-requirements.txt -r requirements/<platform>/sim-requirements.txt

See :git_url:`klayout_package/python/requirements` and :ref:`dependency_extensions` for full list of requirements files.

.. _exclusive_python_environment:

3. KQCircuits exclusive python environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have ``pip-tools`` installed, you can use the ``pip-sync`` command to completely rewrite you python environment
to only use the pinned KQCircuits requirements, removing other packages.
Only do this kind of installation on a virtual environment specifically created for using KQCircuits.

.. code-block:: console

    <activate your virtual environment>
    pip install pip-tools
    cd klayout_package/python
    pip-sync requirements/<platform>/requirements.txt requirements/<platform>/dev-requirements.txt requirements/<platform>/sim-requirements.txt
    python -m pip install --no-deps -e .

``pip-sync`` will completely wipe out your virtual environment,
so you will need to list each requirements file you will need within the single ``pip-sync``
command.

4. PyPI Installation
^^^^^^^^^^^^^^^^^^^^

KQCircuits is also publicly available in the PyPI index and can be installed using:

.. code-block:: console

    pip install kqcircuits

You won't be able to easily modify KQCircuits code and you won't have access to many features such as
simulation scripts and masks.
A new Python package is automatically uploaded to PyPI for every tagged commit in GitHub.

.. _dependency_extensions:

Dependency extensions
^^^^^^^^^^^^^^^^^^^^^

We divided dependencies used by KQCircuits into following categories:

- ``requirements.txt``: Minimal dependencies needed to use core KQCircuits API
- ``dev``, ``dev-requirements.txt``: Dependencies needed to develop and contribute to KQCircuits, including running unit tests (see :ref:`testing`), linter, generating documentation (see :ref:`documentation`) etc
- ``sim``, ``sim-requirements.txt``: Dependencies needed to export and run simulations, see :ref:`export_and_run`
- ``gui-requirements.txt``: Dependencies needed for KQCircuits GUI installation. Do not use manually, this is used by :git_url:`setup_within_klayout.py` and on KLayout startup.

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
standalone KLayout module. With `jupyter <https://pypi.org/project/jupyter/>`__ installed in your environment, run it with:

.. code-block:: console

    jupyter-notebook notebooks/viewer.ipynb


Updating the required dependencies
----------------------------------

Don't do it unless absolutely necessary! The security model (TOFU) works best if
dependencies are rarely changed. When updating dependencies try to verify that
the new versions are legitimate.

Edit the ``*requirements.in`` files according to your needs. Try to keep <=
and == version constraints to a minimum. You can add these constraints temporarily
to force a version update in pre-existing ``*requirements.txt`` files, just remember
to remove these version constraints afterwards, unless they are necessary.

Compile the new ``requirements/<platform>/*requirements.txt`` files for
every source ``*requirements.in`` file you changed (make sure you have ``pip-tools`` installed):

.. code-block:: console

    cd klayout_package/python
    pip-compile --allow-unsafe --generate-hashes --output-file=requirements/<platform>/requirements.txt requirements.in
    pip-compile --allow-unsafe --generate-hashes --output-file=requirements/<platform>/dev-requirements.txt dev-requirements.in
    [...]

Substitute ``<platform>`` with ``win``, ``mac`` or ``linux``. Ideally the files for each supported platform
should get updated, we'd appreciate if you could access a device or virtual image for each of the platforms
to run ``pip-compile`` on them. If you don't have the access, we will do it for you when reviewing the pull request.
It would be also nice if the requirements files are usable on python versions ``3.11.x``, ``3.12.x``, ``3.13.x`` and ``3.14.x``.
This will be tested by github actions before your pull request will get merged.
