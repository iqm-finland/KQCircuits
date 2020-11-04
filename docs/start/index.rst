Getting Started
===============

This section explains the basic installation and usage of KQCircuits with
KLayout Editor. It is also possible to use KQC with the standalone KLayout
python module, for that see :ref:`standalone`.

.. _prerequisites:

Prerequisites
-------------

KLayout
^^^^^^^

Download and install KLayout from https://www.klayout.de/build.html . Builds
should exist there for most common operating systems, choose the correct one
for your OS. Otherwise you need to build KLayout yourself. We will assume in
these instructions, that KLayout has been installed in the default location.
**Note:** you must open KLayout at least once before installing KQCircuits,
because the KLayout python folder is only created then.

Successfully tested versions:

- Linux (Ubuntu 18.04 LTS, 64-bit): KLayout 0.26.4, 0.26.7 and 0.27
- MacOS: KLayout 0.26.3
- Windows 10 (64-bit): KLayout 0.26.3, 0.26.4, 0.26.7

Python
^^^^^^

KQCircuits requires Python 3, which should be already installed on Linux. On
Windows you may have to install it. If your Python installation does not
already contain the ``pip`` package manager, you have to also install that.

Succesfully tested versions:

- Windows: Python 3.7.6, 3.8.5
- Ubuntu 18.04 LTS: Python 3.6.9 and Python 3.8.5

Note, that KLayout is linked together with libpython*.so, that is, it will run
macros with it's own Python version, ignoring virtualenv settings.

Git
^^^

KQC can be used without using Git, but it is required for sharing your code
in https://github.iqm.fi/iqm/KQCircuits .

.. _installation-by-script:

Installation
------------

This section explains basic installation, where the required packages
are automatically installed in the default locations where KLayout looks for
them. If you want to have more control over the installation process, see the
detailed instructions in :ref:`klayout_editor`.

1. If you have not yet done so, ``git clone`` the KQCircuits source code from
https://github.iqm.fi/iqm/KQCircuits to a location of your choice.

2. Open a command line / terminal (in Windows you must open it with
administrator privileges) and ``cd`` to your KQCircuits folder. Then write::

    python3 setup_within_klayout.py

to install KQC. You may have to write ``python`` or ``py`` instead of
``python3`` depending on your OS and Python installation, just make sure that
the command refers to Python 3.


.. _usage:

Usage
-----

To use KQC in KLayout, open KLayout in editing mode (go to
``File->Setup->Application->Editing mode``, check ``use editing mode by
default`` and restart, or launch KLayout(Editor) application if on Windows).
If KQC was installed succesfully, you should then see KQC libraries such as
``Element library`` and ``Chip library`` in KLayout's library browser. The
elements can then be dragged and dropped from there to the layout. For more
detailed instructions, see the followin sections:

.. toctree::
    :glob:

    gui_workflow
    macro_workflow
    xsection
    terminology
