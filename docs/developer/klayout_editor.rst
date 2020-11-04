.. _klayout_editor:

KQCircuits with KLayout Editor
====================================

KQCircuits objects, such as elements and chips, can be viewed and manipulated
in the KLayout Editor GUI. More complicated tasks in KLayout Editor can be
done by writing KLayout macros, which use the KQCircuits library. The code runs
within KLayout's built-in Python interpreter, so debugging must be done in
KLayout's macro IDE.

Prerequisites
-------------

See :ref:`prerequisites`.

Installation
------------

If you have not yet done so, git clone the KQCircuits source code from
https://github.iqm.fi/iqm/KQCircuits to a location of your choice.

To use KQCircuits in KLayout Editor, symlinks must be created from KLayout's
python folder to your KQCircuits folder. There is script for that (see :ref:`installation-by-script`)
which attempts to do the same as explained below.

Some Python packages must also be installed for KQCircuits to work. The
details of these steps for different operating systems are explained in
the following sections.

Linux or MacOS
^^^^^^^^^^^^^^^

Create a symlink from KLayout to kqcircuits by writing in terminal::

    ln -s /path/to/kqcircuits/kqcircuits ~/.klayout/python/kqcircuits
    ln -s /path/to/kqcircuits/scripts ~/.klayout/python/kqcircuits\ macros

To install the required packages, open a terminal in your KQCircuits folder
(which contains ``requirements_within_klayout_unix.txt``), and write::

    pip3 install -r requirements_within_klayout_unix.txt

The previous command installs the packages to your system's default Python
environment, because that is where KLayout looks for the packages on Linux.
If you want to install the packages in a separate environment instead, you
have to create a symlink to there.

Windows
^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a symlink from KLayout to kqcircuits by opening a command prompt with
administrator privileges, and do::

    cd %HOMEPATH%\KLayout\python
    mklink /D 'kqcircuits' "path\to\kqcircuit\kqcircuits"
    mklink /D 'kqcircuits_scripts' "path\to\kqcircuit\scripts"

Install the required packages by opening command prompt in your KQCircuits
folder (which contains ``requirements_within_klayout_windows.txt``), and writing::

    pip install -r requirements_within_klayout_windows.txt --target=%HOMEPATH%\AppData\Roaming\KLayout\lib\python3.7\site-packages

The previous command installs the packages to KLayout's embedded Python
environment, which is where KLayout looks for packages on Windows. If you
want to install the packages in another environment instead, you have to
create a symlink to there.

Some packages, like numpy, must be compiled on the same compiler as the
embedded Python in KLayout. Since KLayout 0.26.2, a correct version of numpy
is already included with KLayout, so this shouldn't be a problem.

Usage
-----

See :ref:`usage`.
