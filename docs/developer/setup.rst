.. _developer_setup:

Developer GUI Setup
===================

Prerequisites
-------------

First install :ref:`klayout`.

If using existing KLayout installation which has KQCircuits Salt package installed, we recommend
to remove such package from the Salt package manager. Two concurrent GUI setups may lead to many
problems such as duplicate macros etc.

Python
^^^^^^

KQCircuits installation requires Python 3.10 minimum. This should already come pre-packaged at least
with Ubuntu 22.04. On Windows platforms Python needs to be installed manually.
If your Python installation does not already contain the ``pip`` package
manager, you have to also install that.

Successfully tested versions:

- Ubuntu 22.04 LTS with Python 3.10.14
- Windows: Python 3.11.2

Sources
-------

Get KQCircuits' sources with:

.. parsed-literal::

    git clone |GIT_CLONE_URL|

Install
-------

This section explains basic installation, where the required packages
are automatically installed in the default locations where KLayout looks for
them. If you want to have more control over the installation process, see section :ref:`manual_installation`.

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

Unlinking
---------

Installation command links your KQCircuits installation with your KLayout
installation automatically. If you wish to unlink, then write in your terminal::

    python3 setup_within_klayout.py --unlink

Update
------

Updating an existing KQCircuits GUI setup is easy. After updating KQCircuits code itself with ``git
pull`` just run :git_url:`setup_within_klayout.py` again. This will take care of upgrading (or downgrading)
KQCircuits' Python dependencies and installing new ones, as needed. Alternatively, KQCircuits dependencies
can be installed by launching KLayout and accepting the window that asks to update dependencies.
This usually requires a KLayout restart afterwards.

The list of dependencies of KQCircuits as KLayout GUI plugin are maintained in ``gui-requirements.txt``
files present in the :git_url:`klayout_packages/python/requirements` folder. These files may evolve
as KQCircuits code evolves.

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

KLayout needs to know about this secondary environment, for example:

    KLAYOUT_HOME=~/.klayout_alt/KQC_2nd klayout

Remember to set up a new ``venv`` before attempting :ref:`standalone` in this directory. Otherwise
your secondary environment may get mixed up with the primary one.

.. _manual_installation:

Manual installation
-------------------

To use KQCircuits in KLayout Editor, symlinks must be created from KLayout's
python folder to your KQCircuits folder. Some Python packages (dependencies) must also be
installed for KQCircuits to work. The details of these steps for different
operating systems are explained in the following subsections. The script
:git_url:`setup_within_klayout.py` used in the previous section attempts to
automatically do the same steps as explained below.

Symlinks in Linux or MacOS
^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a symlink from KLayout to the kqcircuits package and scripts::

    ln -s /Path_to_KQCircuits/klayout_package/python/kqcircuits ~/.klayout/python/kqcircuits
    ln -s /Path_to_KQCircuits/klayout_package/python/scripts ~/.klayout/python/kqcircuits_scripts
    ln -s /Path_to_KQCircuits/klayout_package/python/requirements ~/.klayout/python/kqcircuits_requirements

Symlinks in Windows
^^^^^^^^^^^^^^^^^^^

Create a symlink from KLayout to kqcircuits by opening a command prompt with
administrator privileges, and do::

    cd %HOMEPATH%\KLayout\python
    mklink /D kqcircuits "Path_to_KQCircuits\klayout_package\python\kqcircuits"
    mklink /D kqcircuits_scripts "Path_to_KQCircuits\klayout_package\python\scripts"
    mklink /D kqcircuits_requirements "Path_to_KQCircuits\klayout_package\python\requirements"

(In PowerShell replace the first line by ``cd ~\KLayout\python``)

Installing dependencies
^^^^^^^^^^^^^^^^^^^^^^^

Usually launching KLayout after setting up symlinks will install dependencies for you,
just click Yes on the prompt and maybe restart KLayout again for changes to take effect.
If this won't help, please refer to :ref:`manual_installation_of_klayout_packages`.
Instead of installing each package individually, try installing them in bulk,
by replacing the ``<PACKAGE>==<VERSION>`` part of the ``pip`` command with
``-r klayout_package/python/requirements/<OS>/gui-requirements.txt``, ``<OS>``
being either ``win``, ``mac`` or ``linux``.
