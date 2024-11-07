KQCircuits Layers
=================

KLayout's right panel shows a layer tree. Layers containing meaningful device geometry are grouped
by faces: ``1t1-face``, ``2b1-face`` and ``2t1-face``. By default layer numbers 0-127 are used for
the bottom face of the chips and 128-255 are used for the top face, and the data type indicates the
chip number (data type 0 is used for layers not belonging to chip faces). Other texts, annotations
and miscellaneous things not strictly belonging to a particular face are under the ``texts`` layer
group. Other layers used only for simulations are under the aptly named ``simulations`` layer group.

Most layers have self-describing names like ``refpoints`` or ``instance_names`` but others need a
bit of explanation:

- ``base metal gap wo grid`` -- This is the layer most used in code. Here you place the shapes of gaps
  (areas without metal) in the base metal layer that is laid out on a silicon substrate.

- ``ground grid avoidance`` -- In this layer you should draw shapes that encompass everything in
  ``base metal gap wo grid`` plus a small margin, usually set by the ``margin`` parameter.

- ``groud grid`` -- This layer is auto generated if the "Make ground plane grid" parameter is
  enabled in a chip. It fills in the chip area *outside* of shapes in the ``ground grid avoidance``
  layer with a metal grid. Technically, this layer contains the square shaped gaps in the grid, not
  the metal grid itself. Hidden by default.

- ``base metal addition`` -- In some cases, you want to add metal back where it is already removed by
  another element. This is rarely used, for example in qubits to make sure the junctions connect correctly.

- ``base metal gap`` -- This layer has the final geometry of chips *in masks*. This is generated automatically
  when the "Merge grid and other gaps into base_metal_gap layer" parameter is enabled in chips with the formula:
  ``base_metal_gap = base_metal_gap_wo_grid + ground_grid - base_metal_addition``. In this layer any rounding errors
  in the geometry are also automatically resolved, such that elements that should touch connect without gaps.
  Hidden by default.

Find more details in :git_url:`defaults.py <klayout_package/python/kqcircuits/defaults.py>`.