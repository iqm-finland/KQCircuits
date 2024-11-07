Detailed examples
=================

This section shows more detailed examples of elements and chips.

Example of defining an Element
------------------------------

In Elements, one often uses the `KLayout geometry API <https://www.klayout.de/doc-qt5/code/module_db.html>`_ to define
shapes (such as ``DBox`` and ``DPolygon``), and insert the shapes into the appropriate KQCircuits layers.

Here is an example of defining a new element, with code comments explaining the different parts::

    # Import any modules, classes or functions used in our code.
    from kqcircuits.elements.element import Element
    from kqcircuits.pya_resolver import pya
    from kqcircuits.util.parameters import Param, pdt
    from kqcircuits.util.symmetric_polygons import polygon_with_vsym


    # Any KQCircuits element must inherit from Element.
    class SimpleCross(Element):

        # Define parameters for this class here.
        # Each parameter definition contains the parameter type, description and default value.
        # Other optional data such as the unit can also be defined for parameters.
        arm_length = Param(pdt.TypeDouble, "Cross arm length", 100, unit="μm")

        # The build() function is where the element geometry is built.
        def build(self):
            # We define a hardcoded value for arm_width, so it cannot be changed from outside like arm_length.
            arm_width = 30
            # Define some variables to hold values used commonly in this function.
            len1 = arm_width/2
            len2 = arm_width/2 + self.arm_length
            # Define the cross polygon using a list of DPoints.
            cross_poly = pya.DPolygon([
                pya.DPoint(-len1, -len2),
                pya.DPoint(-len1, -len1),
                pya.DPoint(-len2, -len1),
                pya.DPoint(-len2, len1),
                pya.DPoint(-len1, len1),
                pya.DPoint(-len1, len2),
                pya.DPoint(len1, len2),
                pya.DPoint(len1, len1),
                pya.DPoint(len2, len1),
                pya.DPoint(len2, -len1),
                pya.DPoint(len1, -len1),
                pya.DPoint(len1, -len2),
            ])
            # Add the cross polygon to the cell.
            # We use the get_layer() function to select in which layer the polygon is added.
            self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(cross_poly)

To include this element in the KQCircuits element library, copy this code to a
new Python-file ``simple_cross.py`` in the
``klayout_package/python/kqcircuits/elements`` folder, or in the corresponding folder in your user package if you are
using the Salt installation. After reloading the libraries, ``SimpleCross`` can be used like any other KQCircuits element.

Example of defining a Chip and inserting elements into it
---------------------------------------------------------

Many elements not only create their own geometry from scratch, but also
include other elements as subcells. This is especially true for chips, which
typically use existing elements as building blocks instead of producing shapes
directly. In this example we show how to place instances of the ``SimpleCross``
element created in the previous section into a new chip::

    from kqcircuits.chips.chip import Chip
    from my_package.elements.simple_cross import SimpleCross
    from kqcircuits.pya_resolver import pya


    # New chip implementation must use the Chip element as a base class.
    # As chips are also elements, all the previous explanations about
    # parameters, build-method etc. hold also for them.
    class NewChip1(Chip):

        def build(self):

            # The produce_launchers function creates launchers fitting a certain
            # sampleholder and sets the chip size accordingly. The available
            # sampleholder types are defined in defaults.py (default_sampleholders).
            self.produce_launchers("SMA8")

            # Define variable for half chip width for positioning elements
            half_width = self.box.width()/2

            # Elements can be inserted to other elements (including chips) using the insert_cell function.
            # Giving the class name, instance transformation and parameters, it creates a cell
            # object with the given parameter values and places an instance of that cell inside this cell
            # with the given transformation.
            # (Note that the chip origin is at the bottom left corner of the chip)
            self.insert_cell(SimpleCross, pya.DTrans(half_width, half_width), arm_length=200)

            # Another option is to first create the cell separately using add_element, and then insert
            # instances of that cell using insert_cell. This can be useful when placing many instances
            # with the same parameter values.
            cross_cell = self.add_element(SimpleCross, arm_length=150)
            self.insert_cell(cross_cell, pya.DTrans(half_width - 2000, half_width - 2000))
            self.insert_cell(cross_cell, pya.DTrans(half_width - 2000, half_width + 2000))
            self.insert_cell(cross_cell, pya.DTrans(half_width + 2000, half_width + 2000))
            self.insert_cell(cross_cell, pya.DTrans(half_width + 2000, half_width - 2000))

This code can be copied to a new Python-file ``new_chip1.py`` in the ``chips`` folder to make it visible in the
KQCircuits chip library.


In the previous example we used::

    self.produce_launchers("SMA8")

to make the chip have the correct launchers and size for fitting in an
"SMA8"-type sampleholder. For information on default sample holders and defining custom sample holders, see
:ref:`configure_sample_holders`
