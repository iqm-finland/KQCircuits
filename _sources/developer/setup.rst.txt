.. _developer_setup:

Developer Setup
===============

Prerequisites
-------------

First install :ref:`klayout`.

Developer setup may be done independently from the GUI based installation of the KQCircuits Salt
package. But you should not do both without removing the other one. Otherwise there will be
duplicate macros and possibly other problems.

Python
^^^^^^

KQCircuits installation requires Python 3, which should be already installed on Linux. On Windows
you may have to install it. If your Python installation does not already contain the ``pip`` package
manager, you have to also install that.

Successfully tested versions:

- Ubuntu 18.04 and 20.04 LTS with Python 3.6.9 and Python 3.8.5
- Windows: Python 3.7.6, 3.8.5

Sources
-------

Get KQCircuits' sources with:

.. parsed-literal::

    git clone |GIT_CLONE_URL|

Alternatively, you may re-use the Salt package itself for quick tests, it is under the
``.klayout/salt/KQCircuits`` directory. In this case creating symbolic links or installing some
dependencies may not be required. Beware, a Salt package update **will overwrite your code** in this
directory without any warning!

Install
-------

This section explains basic installation, where the required packages
are automatically installed in the default locations where KLayout looks for
them. If you want to have more control over the installation process, see the
next section.

Open a command line / terminal and ``cd`` to your KQCircuits folder. Then write::

    python3 setup_within_klayout.py

to install KQC. You may have to write ``python`` or ``py`` instead of
``python3`` depending on your OS and Python installation, just make sure that
the command refers to Python 3.

If your Python installation does not already contain the ``pip`` package
manager, you have to also install that too.

Note, that KLayout will run macros with it's own Python version, ignoring
virtualenv settings. KLayout is linked together with libpython*.so on Linux and
libpython*.dll on Windows.

.. note::
   If KQCircuits is not working properly after installation (KQC libraries
   not visible, running any macro gives an error, etc.), there might be some
   problem with the specific KLayout version/build you are using, see
   :ref:`installation_issues` section for possible solutions.

Update
------

Updating an existing KQCircuits setup is easy. After updating KQCircuits code itself with ``git
pull`` just run :git_url:`setup_within_klayout.py` again. This will take care of upgrading (or downgrading)
KQCircuit's Python dependencies and installing new ones, as needed. Running KLayout will similarly
update KQCircuits' dependencies in its own Python environment.

.. note::
    If a new version of KQCircuits has stopped using a certain Python dependency that will **not**
    be removed automatically. The user has to remove that manually if it causes any problem.

Secondary install
-----------------

.. warning::
     Don't do it, unless you really need multiple parallel environments.

It is possible to work with several independent KQC instances simultaneously. You only need to check
out KQCircuits under some different name::

    git clone https://github.com/iqm-finland/KQCircuits KQC_2nd

KLayout needs to know about this secondary environment, run it with :git_url:`startkl.py` or by manualy
setting the environment variable ``KLAYOUT_HOME``::

    KLAYOUT_HOME=~/.klayout_alt/KQC_2nd klayout

Remember to set up a new ``venv`` before attempting :ref:`standalone` in this directory. Otherwise
your secondary environment may get mixed up with the primary one.

Manual installation
-------------------

To use KQCircuits in KLayout Editor, symlinks must be created from KLayout's
python folder to your KQCircuits folder. Some Python packages must also be
installed for KQCircuits to work. The details of these steps for different
operating systems are explained in the following subsections. The script
:git_url:`setup_within_klayout.py` used in the previous section attempts to
automatically do the same steps as explained below.

Linux or MacOS
^^^^^^^^^^^^^^

Create a symlink from KLayout to the kqcircuits package and scripts::

    ln -s /Path_to_KQCircuits/klayout_package/python/kqcircuits ~/.klayout/python/kqcircuits
    ln -s /Path_to_KQCircuits/klayout_package/python/scripts ~/.klayout/python/kqcircuits_scripts

To install the required packages, open a terminal in your KQCircuits folder
(which contains :git_url:`requirements_within_klayout_unix.txt`), and write::

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
    mklink /D kqcircuits "Path_to_KQCircuits\klayout_package\python\kqcircuits"
    mklink /D kqcircuits_scripts "Path_to_KQCircuits\klayout_package\python\scripts"

(In PowerShell replace the first line by ``cd ~\KLayout\python``)

Install the required packages by opening command prompt in your KQCircuits
folder (which contains :git_url:`requirements_within_klayout_windows.txt`), and writing::

    pip install -r requirements_within_klayout_windows.txt --target=%HOMEPATH%\AppData\Roaming\KLayout\lib\python3.7\site-packages

(replace ``python3.7`` in this path by the python version used by your KLayout
version)

The previous command installs the packages to KLayout's embedded Python
environment, which is where KLayout looks for packages on Windows. If you
want to install the packages in another environment instead, you have to
create a symlink to there.

Some packages, like numpy, must be compiled on the same compiler as the
embedded Python in KLayout. Since KLayout 0.26.2, a correct version of numpy
is already included with KLayout, so this shouldn't be a problem.
