Terminology
===========

Full description of KLayout database is in the `API
documentation <https://www.klayout.de/doc-qt5/programming/database_api.html>`__.
Here is a short summary.

#. Cell : Every structure that contains shapes or other cells inside is
   called a cell.
#. PCell : Every cell that is parameterizable and contains shapes, cells
   or PCells inside is called a PCell.
#. Shape : KLayout geometry primitive, such as point, box, line, polygon
   etc.
#. Point : The most basic Shape of KLayout. By using multiple points, it
   is possible to create Boxes and Polygons.
#. Macro : A script you can run in KLayout environment. Can use
   definitions from libraries. Can appear in KLayout GUI menus.
#. Chips : Chip corresponds to a single quantum circuit we can embed in
   the package for experimentation. Preferably implemented by a PCells,
   but some are manually drawn Cells.
#. Mask : Mask is an object used in optical lithography when producing
   an array of Chips onto a silicon wafer. If a physical mask is
   produced, exported design files are archived and code revision is
   tagged for traceability.
#. Top Cell : top\_cell is the cell that works as a main container for
   the other cells and for instance masks can be thought of top cells
   that contain other Pcell structures such as pixels/chips.
