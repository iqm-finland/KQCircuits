Point-and-click workflow tutorial
=================================

This is a step by step tutorial to demonstrate basic workflow with
KQCircuits in KLayout Editor. It is assumed that KLayout and KQCircuits are
already installed.

Do not assume all of the GUI makes sense. At the moment KLayout is
version 0.27! It is already quite powerful, but most features make sense
only after you know the API.

#. **Generate Demo chip**

   #. Run KLayout Editor. On Windows you should have separate shortcuts
      for KLayout Viewer and KLayout Editor. On Linux you may have to go
      to *File -> Setup -> Application -> Editing Mode* and set *Use
      editing mode by default* to true, and restart KLayout.
      On macOS click on KLayout and on the top right corner click 
      *Preferences -> Application -> Editing Mode -> Use editing mode by default*.
      Then restart the KLayout program.
   #. In the *Libraries* panel on the bottom left, choose *Chip Library* and drag
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

#. **Change a location of a qubit.**

   #. Press ``F2`` to see the whole top cell.
   #. Locate the qubit in the top left part of the chip.
   #. Drag a selection box around the qubit.
   #. From the *Tools* panel select *Move*.
   #. Click on the selection box.
   #. Click on a new location for a qubit.

#. **Disable a coupling port for the qubit.**

   #. From the *Tools* panel select *Select*.
   #. Drag a selection box around the qubit.
   #. Click ``Shift+F2``
   #. Press ``q``.
   #. In the new *Instance Properties* window locate a tab *PCell
      parameters*.
   #. Scroll down in the list of parameters to locate *Coupler lengths*.
   #. Change the value in the text box to ``100,160,0``.
   #. Click ``Ok``.

#. **Create a new qubit.**

   #. Press ``F2`` to see the whole top cell.
   #. From the toolbar select *Instance*.
   #. In the new *Editor Options* window locate *Library*.
   #. Using the drop-down menu select *Qubit Library*.
   #. Click on a button ``🔍`` a little bit to the left from the *Library* 
      for older versions click ``...`` a little bit to the left from the.
      *Library*.
   #. From the new *Select Cell* window select *Swissmon* and press
      *Ok*.
   #. In the *Object Edit or Options* window press *Ok*.
   #. Click at the location of the new qubits.
   #. Click ``Esc`` to finish placing qubits.

#. **Add the ground grid.**

   #. In the top menu, navigate to *KQCircuits -> Fill with ground plane grid*. It may take some time to generate.
      Unhide ground grid in layers list located in the top right.
