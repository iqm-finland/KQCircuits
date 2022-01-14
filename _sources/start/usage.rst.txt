.. _usage:

Usage
-----

KQCircuits objects, such as elements and chips, can be viewed
and manipulated in the KLayout Editor GUI. More complicated tasks in KLayout
Editor can be done by writing KLayout macros, which use the KQCircuits
library. The code runs within KLayout's built-in Python interpreter, so
debugging must be done in KLayout's macro IDE if using KLayout GUI. Note that
the macros `can also be run from the command line without GUI (-z and -r)
switches <https://klayout.de/command_args.html>`__, which allows using other
debugging tools.

To use KQC in KLayout, open KLayout in
`editing mode <https://www.klayout.de/doc/manual/edit_mode.html>`__ (go to
``File->Setup->Application->Editing mode``, check ``use editing mode by
default`` and restart, or launch KLayout(Editor) application if on Windows).
If KQC was installed successfully, you should then see KQC libraries such as
``Element library`` and ``Chip library`` in KLayout's library browser. The
elements can then be dragged and dropped from there to the layout.
The parameters of an element in the layout can be changed by double-clicking
it. For more detailed instructions, see the :ref:`user_guide`.

Modifying or Creating Elements or Chips
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

KLayout Salt packages are read-only. The user may open a chosen chip (say, ``[Package
KQCircuits]/kqcircuits/chips/simple``) with the embedded macro editor (``F5``) but it can not be
directly changed here. Of course, external code editors may be used to change these files or their
copies. On the downside, package upgrades may override these changes.

An other option is to copy (drag-and-drop) the Simple chip to the ``[Local]`` folder with the
embedded macro editor. This copy may be freely changed with the macro editor. First suggested change
would be to rename the chip. This is still not part of KQC. To
make it visible in KLayout we need to create a *symbolic link* to it from the designated chip folder
in ``[Package KQCircuits]/kqcircuits/chips/``. Finally, KLayout should re-read the now update KQC
library, this may be achieved by restarting or with the ``Edit -> KQCircuits Library -> Reload
libraries`` menu entry.

It may take a bit of effort to find where these folders are in a particular OS, in Linux::

    cd $HOME/.klayout/salt/KQCircuits/python/kqcircuits/chips
    ln -s $HOME/.klayout/pymacros/simple.py simpler.py

or in Windows::

    cd %HOME%/KLayout/salt/KQCircuits/python/kqcircuits/chips
    mklink simpler.py "%HOME%/KLayout/pymacros/simple.py"

Naturally, the same approach would work to copy/create other elements, qubits etc. Creating macros or
masks is even easier, no need to fumble with external editors or symlinks the default ``[Local]``
folder may be directly used to run the copied and modified macro or mask generation script. But for
serious development work we suggest following the :ref:`developer_setup`.
