Installation
============

If you have not yet done so, ``git clone`` the KQCircuits source code from
https://gitlab.iqm.fi/iqm/qe/KQCircuits to a location of your choice.

Basic automatic installation
----------------------------

This section explains basic installation, where the required packages
are automatically installed in the default locations where KLayout looks for
them. If you want to have more control over the installation process, see the
next section.

Open a command line / terminal (in Windows you must open it with
administrator privileges) and ``cd`` to your KQCircuits folder. Then write::

    python3 setup_within_klayout.py

to install KQC. You may have to write ``python`` or ``py`` instead of
``python3`` depending on your OS and Python installation, just make sure that
the command refers to Python 3.

Manual installation
-------------------

To use KQCircuits in KLayout Editor, symlinks must be created from KLayout's
python folder to your KQCircuits folder. Some Python packages must also be
installed for KQCircuits to work. The details of these steps for different
operating systems are explained in the following subsections. The script
``setup_within_klayout.py`` used in the previous section attempts to
automatically do the same steps as explained below.

Linux or MacOS
^^^^^^^^^^^^^^

Create a symlink from KLayout to kqcircuits by writing in terminal::

    ln -s /path/to/kqcircuits/kqcircuits ~/.klayout/python/kqcircuits
    ln -s /path/to/kqcircuits/scripts ~/.klayout/python/kqcircuits_scripts

To install the required packages, open a terminal in your KQCircuits folder
(which contains ``requirements_within_klayout_unix.txt``), and write::

    pip3 install -r requirements_within_klayout_unix.txt

The previous command installs the packages to your system's default Python
environment, because that is where KLayout looks for the packages on Linux.
If you want to install the packages in a separate environment instead, you
have to create a symlink to there.

Windows
^^^^^^^

Create a symlink from KLayout to kqcircuits by opening a command prompt with
administrator privileges, and do::

    cd %HOMEPATH%\KLayout\python
    mklink /D 'kqcircuits' "path\to\kqcircuits\kqcircuits"
    mklink /D 'kqcircuits_scripts' "path\to\kqcircuits\scripts"

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
