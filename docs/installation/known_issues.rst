
.. _installation_issues:

Known installation issues
-------------------------

For some specific KLayout builds there can be problems with KQCircuits
installation that require some extra steps:

* Standard KLayout installation package for MacOS (``ST-klayout-*``)
  is compiled to use the system Python dynamic library, which for
  Sonoma version still has Python version 3.9. ``networkx`` dependency is only supported
  on Python version 3.10 and higher. We recommend using heavyweight KLayout
  package (``HW-klayout-*``) that uses compatible Python, but if that is not an option, you can comment
  out the ``networkx`` entry in :git_url:`gui-requirements.txt <klayout_package/python/requirements/mac/gui-requirements.txt>`
  to proceed with installation.
  Currently this only prevents using the :git_url:`netlist_as_graph.py <util/netlist_as_graph.py>` script.
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

    ``pip install <PACKAGE>==<VERSION> --target=<KLAYOUT-PACKAGE-DIR> --python-version <KLAYOUT-PYTHON-VERSION> --platform <KLAYOUT-PLATFORM> --only-binary=:all: --upgrade``

The KLAYOUT-PACKAGE-DIR should be the path to the site-packages directory
used by KLayout. If you don't know where that is, you can find it by opening
the KLayout macro editor and writing ``import setuptools`` and then ``setuptools.__path__``
in the console.

KLAYOUT-PYTHON-VERSION may expect a different version than the Python version you use in the terminal,
so it's best to query that from KLayout macro editor: ``import sys``, ``sys.version_info``.

On other operating systems than MacOS the ``--platform`` argument can be omitted.
However Mac distributions of KLayout are compiled on ``x86_64`` CPU architecture,
while many modern macbooks have ``M2`` or other CPU architecture. Hence some dependencies
like ``numpy`` and ``scipy`` need to be compiled for platform ``macosx_10_9_x86_64``,
even when ``pip`` will by default fetch distributions compiled for ``macosx_10_9_arm64``.

Notice that this only affects the GUI installation of KQCircuits.
The standalone, GUI-less KQCircuits installation will use whatever Python environment
where it was explicitly installed in, which is most likely separate from the Python
environment used by KLayout. It is even recommended to install standalone KQCircuits
into a virtual environment.
