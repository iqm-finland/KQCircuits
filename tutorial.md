# Quick start guide
This is a step by step tutorial to demonstrate basic workflow with KQCircuit. It is assumed that KLayout and KQCircuit are already installed. 

Do not assume all of the GUI makes sense. At the moment KLayout is version 0.25! It is already quite powerful, but most features make sense only after you know the API.

1. Generate Demo chip
    1. Run KLayout
    2. In the top menu, navigate to _Edit->KQCircuit->Demo chip_.
2. For _drag and drop_ changed, convert the _top cell_ to _static_.
    1. Locate _Cells_ panel on the left.
    2. Left click on the cell named `KQChip.TestChip` to select it.
    3. In the top menu, navigate to _Edit->Cell->Convert to Static Cell_. This converts a _library cell_ into a locally defined cell and enables you to edit it. This action emptied the layout view as the old _top cell_ no longer exists. 
    4. In the _Cells_ panel right, click on the cell named `Test$1`.
    5. From the drop down menu, select _Show as new top_.
3. Change the shape of the waveguide.
    1. In the _Layout_ panel locate the charge line of the qubit. It connects the top left launcher and the qubit.
    2. Click once on the charge line to select it.
    3. Press `Shift+F2` to zoom in.
    4. From the _Tools_ panel above the _Layout_ panel select a tool _Partial_.
    5. Double click on the center of the charge line. A new node should appear there.
    6. Drag the new node with the mouse. The waveguide should change shape.
4. Change a location of a qubit.
    1. Press `F2` to see the whole top cell.
    2. Locate the qubit in the top left part of the chip.
    3. From the _Tools_ panel select _Move_.
    4. Click on the qubit.
    6. Click on a new location for a qubit.
5. Enable extra coupling port for the qubit.
    1. From the _Tools_ panel select _Select_.
    2. Click once on the qubit.
    3. Click `Shift+F2`
    4. Double-click on the qubit.
    5. In the new _Object Properties_ window locate a tab _PCell parameters_.
    6. Scroll down in the list of parameters to locate _Coupler lengths_.
    7. Change the value in the text box to `100,160,0`.
    8. Click `Ok`.
6. Create a new qubit.
    1. Press `F2` to see the whole top cell.
    2. From the _Tools_ panel select _Instance_.
    3. In the new _Object Edit or Options_ window locate _Library_.
    4. Using the drop-down menu select _KQCircuit_.
    5. Click on a button `...` a little bit to the left from the _Library_. 
    6. From the new _Select Cell_ window select _Swissmon_ and press _Ok_.
    7. In the _Object Edit or Options_ window press _Ok_.
    8. Click at the location of the new qubits.
    9. Click `Esc` to finish placing qubits.
7. Add the ground grid.
    1. In the top menu, navigate to _Edit->KQCircuit->Fill with ground plane grid_.
    