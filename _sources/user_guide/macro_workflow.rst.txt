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

Basic workflow
--------------

#. Open the KLayout application
#. From the top menu, choose "Macros" and "Macro Development", or press F5.
#. Select "Python"
#. Open "[Local - python branch]", where you should see the "kqcircuits scripts"
   directory
#. Open :git_url:`kqcircuits_scripts/macros/generate/demo_placing_a_pcell.lym <klayout_package/python/scripts/macros/generate/demo_placing_a_pcell.lym>`
#. Click on the green play symbol with the exclamation mark ("Run script
   from the current tab"), or use Shift+F5.
#. A chip cell should appear in the main KLayout window.


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
