Useful commands
===============

Hotkeys
-------

Use the following hotkeys to navigate around, and if not all parts of the geometry are visible:

- ``*`` makes the full cell hierarchy visible. Otherwise only cell frames may be
  visible. Also accessible from *Display* -> *Full hierarchy* in the top menu.
- ``F2`` zooms to show the full layout (from the current top cell)
- ``Shift+F2`` zooms to show the currently selected cell


KQCircuits menu
---------------

Several very useful macros are directly accessible from KLayout's "**KQCircuits**"
drop-down menu:

- **Empty layout with a top cell and default layers** -- A new layout in KLayout is empty and has no
  assigned layers by default. This macro helps to create a more useful new layout with a predefined
  top-cell and the default KQCircuits layers.

- **Fill with ground plane grid** -- Creates a ground plane grid covering the top cell bounding box,
  except the parts in grid avoidance layer. Requires at least one cell to exist in the current
  layout. Only creates the grid for "1t1"-face. Remember to unhide the 1t1_ground_grid layer to make it
  visible.

- **All chips in the library** -- Opens a new layout and puts all available chips there arranged in
  a grid. Note that this operation may take several minutes.

- **Reload libraries** -- Reloads KQCircuits code from storage making it possible to modify elements
  and see the change without having to restart KLayout and reload the edited elements. This is
  illustrated in the end of previous section's video. Note that this macro does
  not reload the KQCircuits :git_url:`defaults <klayout_package/python/kqcircuits/defaults.py>`
  file.

- **Measure waveguide lengths** -- Opens the waveguide length tool. KQCircuits waveguides define path shapes in
  dedicated layers which have the length of the waveguide, including any smooth corners and meanders. The waveguide
  length tool changes the selection mode such that the user can select these paths, and shows the total length of
  selected waveguide paths in a dialog window. Close the dialog to return to normal selection modes.

- **Show errors on cell** -- Some KQCircuit elements show error messages in the ``annotations`` layer if the geometry
  cannot be drawn, for example a waveguide segment does not fit with the chosen path and corner radius. This macro lists
  all errors in the current layout in a dialog box, including the cell hierarchy path leading up to the cells raising
  errors.

DRC scripts are accessible from KLayout's "**Tools -> DRC** drop-down menu:

- **Area and Density** -- Calculate area and density for everything in view, in every layer.
- **Waveguide** -- Detects Waveguides crossing anything in base_metal_gap_wo_grid layer.
