Manual workflow tutorial
========================

In this step-by-step example, we show how to use an existing chip in the KLayout GUI, and manually modify the elements
on the chip.

.. note::
   This workflow results in a static geometry, which no longer corresponds to the python code that defined the original
   chip. In the section :ref:`python_start` we will show how to create chips in python code.

   This manual workflow can be also used as a starting point for a new chip. See :ref:`gui_elements_to_code` to learn
   how to generate python code from the static chip.


Generate ``Demo`` chip
----------------------

#. Open KLayout in editing mode (see :ref:`usage`)
#. In the *Libraries* panel on the bottom left, choose *Chip Library* and drag and drop the *Demo* chip from there to
   the layout.
#. Click *Ok* in the *PCell parameters* window that opens.

Convert the chip cell to static
-------------------------------

We now have a parametrized chip cell placed in the layout. We can change the parameters of the chip, but not manually
edit the elements and geometry `inside` the chip. To edit the elements manually, we convert it to a static cell:

#. Locate *Cells* panel on the left.
#. Left click on the cell named ``ChipLibrary.Demo`` to select it.
#. In the top menu, navigate to *Edit->Cell->Convert to Static Cell*.
#. In the *Cells* panel, right click on the cell named ``Demo$1``.
#. From the drop down menu, select *Show as new top*.

Note that this is a one-way process, a static cell cannot be converted back to a PCell.

The elements inside the ``Demo$`` cell, such as qubits and waveguides, are still PCells, and we will change their
parameters to modify the geometry in the following steps.

Change the shape of a waveguide
-------------------------------

Waveguides follow a path of nodes, which can be edited with the *Partial* tool

#. In the *Layout* panel locate a charge line of the qubit. It connects the top left launcher and the qubit.
#. Click once on the charge line to select it.
#. Press ``Shift+F2`` to zoom in.
#. From the *Tools* panel above the *Layout* panel select a tool *Partial*.
#. Double click on the center of the charge line. A new node should appear there.
#. Drag the new node with the mouse. The waveguide should change shape.

See :ref:`gui_waveguides` for more details.

Change the location of an element
---------------------------------

Elements can be moved with the *Move* tool. For example, to move a qubit:

#. Press ``F2`` to see the whole top cell.
#. Locate the qubit in the top left part of the chip.
#. Drag a selection box around the qubit.
#. From the *Tools* panel select *Move*.
#. Click on the selection box.
#. Click on a new location for a qubit.

Modify element parameters
-------------------------

The parameters of each element can be modified as follows:

#. From the *Tools* panel select *Select*.
#. Drag a selection box around the qubit.
#. Click ``Shift+F2``
#. Press ``q``.
#. In the new *Instance Properties* window locate a tab *PCell parameters*.
#. Scroll down in the list of parameters to locate *Coupler lengths*.
#. Change the value in the text box to ``100,160,0``.
#. Click ``Ok``.

Add new elements
----------------

Here, we add a new qubit.

#. Press ``F2`` to see the whole top cell.
#. From the toolbar select *Instance*.
#. In the new *Editor Options* window locate *Library*.
#. Using the drop-down menu select *Qubit Library*.
#. Click on a button ``🔍`` a little bit to the left from the *Library*  for older versions click ``...`` a little
   bit to the left from the. *Library*.
#. From the new *Select Cell* window select *Swissmon* and press *Ok*.
#. In the *Object Edit or Options* window press *Ok*.
#. Click at the location of the new qubits.
#. Click ``Esc`` to finish placing qubits.

Adding ground grid
-------------------

KQCircuits can generate a standard flux pinning grid on all ground plane areas. If you plan to convert the layout
to python code, you can skip this step - in that case the ground grid can be added during mask export.

If you want to use the static layout for fabrication, you can add the ground grid as follows. Do this as the very last
step.

#. In the top menu, navigate to *KQCircuits -> Fill with ground plane grid*. It may take some time to generate.
   Unhide ground grid in layers list located in the top right.
