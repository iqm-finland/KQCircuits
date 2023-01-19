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
it.
