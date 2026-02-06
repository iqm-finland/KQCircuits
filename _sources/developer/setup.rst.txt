.. _developer_setup:

Developer GUI Setup
===================

With the KQCircuits developer GUI setup, you will have many visual and interactive KQCircuits features
available when you launch the KLayout GUI application, such as
previewing the KQCircuits element and chip libraries, studying how
changing PCell parameters affect the element design and manually routing waveguides on your chip. In addition
to enabling all features you would get from installing :ref:`salt_package` -
with the developer setup, any change you make in cloned KQCircuits code
will take effect after KLayout application is restarted or ``Reload Libraries`` action is run.
In this setup you can amend or create new KQCircuits features which you are welcome to share with us!

The Developer GUI setup will **not** enable some KQCircuits features that work best when executed from a terminal -
for example generating mask sets or exporting and executing simulations are enabled with :ref:`standalone`.
In standalone setup you will also get access to KQCircuits as a python library, which you can
import into your own codebase.

Prerequisites
-------------

First go through :ref:`klayout`. Please also verify that your python version is in order.

If using existing KLayout installation which has KQCircuits Salt package installed, we recommend
to remove such package from the Salt package manager. Two concurrent GUI setups may lead to many
problems such as duplicate macros etc.

Sources
-------

Get KQCircuits' sources (if you haven't already) with:

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

In most cases, after KQCircuits code has been modified (either with ``git pull`` or by manually changing the code),
it is enough to restart the KLayout application or to run the ``Reload Libraries`` action.

If a requirement library has been added, or its version
updated in :git_url:`klayout_package/python/requirements/linux/gui-requirements.txt`, further action may be required.
KLayout will compare dependencies it detected in its system with the contents of this file, and ask the user
to upgrade (or downgrade) the requirements. It is recommended to click Yes, and it may require another KLayout
restart for requirement upgrades to take effect.
You can also run :git_url:`setup_within_klayout.py` again to manually prompt the requirement upgrade.

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
