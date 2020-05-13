KQCircuits with KLayout standalone Python module
======================================================

KQCircuits can be used without KLayout Editor by using the standalone KLayout
Python module. This lets you develop and use KQCircuits completely within any
Python development environment of your choice, without running KLayout GUI.
For example, any debugger can then be used and automated tests can be performed.
The KQCircuits elements can also be visualized using any suitable viewer or
library during development.

Prerequisites
-------------

If you want to run KQCircuits outside of the KLayout Editor, you will need
a Python 3 installation.

Successfully tested with

- Python 3.7.6

Installation
-------------

If you have not yet done so, git clone the KQCircuits source code from
https://github.iqm.fi/iqm/KQCircuits to a location of your choice.

Next, you should install the packages required by KQCircuits using pip and
the ``requirements.txt`` in KQCircuits folder. Note, that there might be
problems with some packages depending on your Python environment. In this case,
make sure your Python version is a version we have successfully tested. If
there is still problems, you can try to avoid using some of the packages
listed in ``requirements.txt``. The purpose of different packages is
commented in ``requirements.txt``.

The following sections give more detailed installation instructions for
specific Python environments.

Installation using Conda
^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you use Anaconda, you can make an environment for KQCircuits::

    conda create --name kqcircuits
    conda activate kqcircuits
    conda install pip

Next, you want to install the packages form requirements.txt. In principle you
want to do::

    pip install -r "path\to\kqcircuit\requirements.txt"

However, chances are (like now) that some package gives an error. I had more
luck installing the latest version of each package manually::

    pip install Autologging cairosvg klayout numpy pytest pytest-cov sphinx sphinx-rtd-theme

On windows compiling `gdspy` from source is not trivial, but you
can download a pre-compiled wheel from [here](https://github.com/heitzmann/gdspy/releases)
and install the wheel as::

    pip install "path\to\wheel.whl"

You may want/need to install other packages here, such as jupyter notebook.

For any external packages, you can link to the Anaconda environment you just
created. In particular we need autologging::

    mklink autologging.py "%HOMEPATH%\Anaconda3\envs\kqcircuits\Lib\site-packages\autologging.py"

Usage
-----

The independence from KLayout GUI makes it possible to do all development of
KQCircuits fully within a Python IDE of your choice. For example, standalone
debuggers and automated testing (see :ref:`testing`) can be done, which would
not be possible without the standalone KLayout module.

There is an example Jupyter notebook ``viewer.ipynb`` in the notebooks
folder, which shows how to create and visualize KQCircuits elements with the
standalone KLayout module. Any other files in the notebooks folder will be
ignored by git, so you can create your own notebooks based on ``viewer.ipynb``
in that folder.