Point-and-click workflow tutorial
=================================

This is a step by step tutorial to demonstrate basic workflow with
KQCircuits in KLayout Editor. It is assumed that KLayout and KQCircuits are
already installed.

Do not assume all of the GUI makes sense. At the moment KLayout is
version 0.26! It is already quite powerful, but most features make sense
only after you know the API.

#. **Generate Demo chip**

   #. Run KLayout Editor. On Windows you should have separate shortcuts
      for KLayout Viewer and KLayout Editor. On Linux you may have to go
      to *File -> Setup -> Application -> Editing Mode* and set *Use
      editing mode by default* to true, and restart KLayout.
   #. In the *Libraries* panel on the left, choose *Chip Library* and drag
      and drop the *Demo* chip from there to the layout.
   #. Click *Ok* in the *PCell parameters* window that opens.

#. **For drag and drop changes, convert the top cell to static.**

   #. Locate *Cells* panel on the left.
   #. Left click on the cell named ``ChipLibrary.Demo`` to select it.
   #. In the top menu, navigate to *Edit->Cell->Convert to Static Cell*.
      This converts a *library cell* into a locally defined cell and
      enables you to edit it.
   #. In the *Cells* panel, right click on the cell named ``Demo$1``.
   #. From the drop down menu, select *Show as new top*.

#. **Change the shape of a waveguide.**

   #. In the *Layout* panel locate a charge line of the qubit. It
      connects the top left launcher and the qubit.
   #. Click once on the charge line to select it.
   #. Press ``Shift+F2`` to zoom in.
   #. From the *Tools* panel above the *Layout* panel select a tool
      *Partial*.
   #. Double click on the center of the charge line. A new node should
      appear there.
   #. Drag the new node with the mouse. The waveguide should change
      shape.

   .. note::
    * You may still see also the old waveguide shape, because of how chips are
      currently implemented in KQC. To hide it, hide the "b base metal gap"
      layer in the *Layers* panel to the right.
    * Some other waveguides in the demo chip are "composite waveguides",
      which contain both "simple waveguides" and other types of elements,
      such as airbridges. Their shape cannot be modified in the same way.
      They can be converted to static cells and then the shapes of the simple
      waveguide cells inside them can be modified.

#. **Change a location of a qubit.**

   #. Press ``F2`` to see the whole top cell.
   #. Locate the qubit in the top left part of the chip.
   #. From the *Tools* panel select *Move*.
   #. Click on the qubit.
   #. Click on a new location for a qubit.

#. **Disable a coupling port for the qubit.**

   #. From the *Tools* panel select *Select*.
   #. Click once on the qubit.
   #. Click ``Shift+F2``
   #. Double-click on the qubit.
   #. In the new *Object Properties* window locate a tab *PCell
      parameters*.
   #. Scroll down in the list of parameters to locate *Coupler lengths*.
   #. Change the value in the text box to ``100,160,0``.
   #. Click ``Ok``.

#. **Create a new qubit.**

   #. Press ``F2`` to see the whole top cell.
   #. From the *Tools* panel select *Instance*.
   #. In the new *Object Editor Options* window locate *Library*.
   #. Using the drop-down menu select *Element Library*.
   #. Click on a button ``...`` a little bit to the left from the
      *Library*.
   #. From the new *Select Cell* window select *Swissmon* and press
      *Ok*.
   #. In the *Object Edit or Options* window press *Ok*.
   #. Click at the location of the new qubits.
   #. Click ``Esc`` to finish placing qubits.

#. **Add the ground grid.**

   #. In the top menu, navigate to *Edit->KQCircuits Library->Fill with ground
      plane grid*. It may take some time to generate.
