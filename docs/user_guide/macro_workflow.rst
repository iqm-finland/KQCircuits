Macro development
=================

KLayout macros are Python scripts which can be run inside KLayout Editor.
They can be used, for example, to create or modify elements in the layout,
measure properties of cells, or export data from the layout. See also the
KLayout documentation about `macro development
<https://www.klayout.de/doc-qt5/about/macro_editor.html>`__ and
`programming scripts <https://www.klayout.de/doc-qt5/programming/index.html>`__
, and the `KLayout API documentation
<https://www.klayout.de/doc-qt5/code/index.html>`__.

Running the first example
-------------------------

To get started, follow the steps below to run a demo macro. The comments in the macro explain what is going on step by
step.

#. Open the KLayout application
#. From the top menu, choose "Macros" and "Macro Development", or press F5.
#. Select "Python"
#. Open "[Local - python branch]", where you should see the "kqcircuits scripts"
   directory
#. Open :git_url:`kqcircuits_scripts/macros/generate/demo_placing_a_pcell.lym <klayout_package/python/scripts/macros/generate/demo_placing_a_pcell.lym>`
#. Click on the green play symbol with the exclamation mark ("Run script
   from the current tab"), or use Shift+F5.
#. A chip cell should appear in the main KLayout window.

Interacting with the KLayout application
----------------------------------------
KLayout organizes layouts in *Panels*, which show as tabs in the application if more than one panel is open.
In code, the panel is represented by a ``LayoutView`` object. Inside each panel there can be one or more
layouts loaded, for example with the *File*, *Open in Same Panel* command. Each layout is represented by a
``CellView`` object and a ``Layout`` object. The ``Layout`` contains all the actual cells, layers and shapes.

As shown by the above, to work with the KLayout display in macro code we need access to at least three objects.
To help in managing this, KQCircuits provides the class :class:`.KLayoutView`.

Creating a new panel
^^^^^^^^^^^^^^^^^^^^
Often, in a macro you want to start with a new layout in a new panel, which can be created as follows::

    from kqcircuits.klayout_view import KLayoutView
    view = KLayoutView()

This code creates a panel, cell view and layout, and initializes these with the layers used by KQCircuits.

Accessing the currently active panel
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In some macros you may want to interact with the layout that is currently visible. In this case, use::

    from kqcircuits.klayout_view import KLayoutView
    view = KLayoutView(current=True)

Using ``KLayoutView``
^^^^^^^^^^^^^^^^^^^^^
Once created, :class:`.KLayoutView` exposes methods for the most common tasks to do with a layout:

- ``insert_cell`` places KQCircuits elements into the top cell, similar to ``Element.insert_cell``.
- ``focus`` makes sure a particular cell or the entire layout is visible (zoom to fit and show all hierarchy levels).
- ``show`` shows the panel associated with this object, in case there are multiple panels open
- ``export_pcell_png`` exports an image of a cell to a file

See the :class:`.KLayoutView` API documentation for all methods and their usage.

If more advanced interaction with KLayout is needed, the KLayout API objects are exposed as properties. See the
corresponding KLayout API documentation linked below for their usage details:

- ``layout_view``: The `LayoutView <https://www.klayout.de/doc-qt5/code/class_LayoutView.html>`__ instance, which refers
  to a panel in the KLayout GUI.
- ``cell_view``: The `CellView <https://www.klayout.de/doc-qt5/code/class_CellView.html>`__ instance. In case a
  panel has multiple cell views (for example when multiple files are opened in the same panel), this returns the
  currently active one.
- ``layout``: The `Layout <https://www.klayout.de/doc-qt5/code/class_Layout.html>`__ object is the main container for
  cells, layers and geometry
- ``top_cell``: A reference to the first top `Cell <https://www.klayout.de/doc-qt5/code/class_Cell.html>`__ of the layout. This is the very first cell shown in the cell window.
  Usually we place elements in this cell.
- ``active_cell``: A reference to the currently active cell. This is the cell which is shown in bold in the cell
  window, and can be changed in KLayout by right-clicking a cell and choosing *Show As New Top*.

Debugger
--------

KLayout macros can be debugged using the debugger in the macro IDE. The
debugger can be toggled on/off using the "bug icon" at the top.

- Basic debugger workflow

    #. Place breakpoint in the code (red circle icon or F9).
    #. Run the macro.
    #. Execution will stop at the breakpoint. The values of all variables at
       that point are now visible in the "Local variables" panel. You can also
       double-click on the lines in the "Call stack" panel, to see variable
       values at other stages of the call stack.
    #. Can place more breakpoints, and the macro will stop at the next one
       when you run the macro again.
    #. Can also use the "Step over" and "Step into" buttons (icons with
       arrows inside files or F) to go through the code step-by-step.

- If an exception is raised when running a macro, you will get a pop-up
  error window. By pressing "Cancel", you will get the debugger view at the
  point where the exception was raised, as if there was a breakpoint there.

- PCells can sometimes have errors in their code, which will be visible in
  the layout as missing parts and an asterisk at the end of the cell name.
  These errors can be caught by having the macro window open and debugger on
  when the PCell is placed into the layout.

  .. note::
   - For this to work the PCell must be created from instance menu on
     the top. If the PCell is dragged from "Libraries" panel, KLayout will
     become unresponsive after the error is caught.
   - Errors will not be caught if creating a new PCell with the exact same
     parameters as a previous one, because the PCell code runs only the first
     time it is created.

.. note::
 The debugger will slow down code execution, so it can make sense
 to disable it when running heavy macros.


Reloading libraries
-------------------

- Even though you have changed some line inside a PCell file, if
  nothing changes on the generated design inside the editor, you have to re-run
  the :git_url:`reload.lym <klayout_package/python/scripts/macros/reload.lym>` file to be able to reload the library features for
  changes to be updated. The reload macro can also be run from
  "KQCircuits -> Reload libraries" in the main KLayout window

- The libraries are automatically reloaded whenever you restart KLayout, so
  in that case there is no need to run the :git_url:`reload <klayout_package/python/scripts/macros/reload.lym>` macro to see changes.

Examples
--------

- Locate the :git_url:`demo_placing_a_pcell <klayout_package/python/scripts/macros/generate/demo_placing_a_pcell.lym>`
  and :git_url:`demo_pya_basic <klayout_package/python/scripts/macros/generate/demo_pya_basics.lym>` tutorials under
  :git_url:`klayout_package/python/scripts/macros/generate` directory. Use the tutorials to have basic understanding
  about KLayout Editor and macro generation concept.

- Some other macros, such as :git_url:`test_waveguide_composite <klayout_package/python/scripts/macros/generate/test_waveguide_composite.lym>` and
  :git_url:`test_wgc_airbridge <klayout_package/python/scripts/macros/generate/test_wgc_airbridge.lym>`, can be useful to learn more about specific KQC
  elements.
