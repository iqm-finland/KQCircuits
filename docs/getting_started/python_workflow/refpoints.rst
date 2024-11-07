.. _python_workflow_refpoints:

Refpoints
=========

In KQCircuits, each elements defines refpoints. Refpoints are locations in the element which are labelled with a name,
and they central way to connect elements together or place elements in relation to each other.

Using refpoints
---------------

In an Element definition ``refpoints`` is just a dictionary of points. You can add a new refpoint by
assigning a point to a name, ``self.refpoints['name'] = pya.DPoint(...)``.

There are several ways the refpoints are used:

- The dictionary of a particular Element instance is returned by ``self.insert_cell()``. So you can
  insert a cell and then use the refpoints as references where to place other elements in relation
  to them.
- If you pass an ``inst_name`` argument to ``insert_cell()`` the refpoints are also named uniquely
  for the instance as ``{inst_name}_{refpoint_name}`` and added as text instances to the layout.
  This way you can later look up the points by name.
- ``insert_cell`` also has a ``rec_levels`` argument which determines now many layers down the
  hierarchy the refpoints are added.

As an example of using refpoints, let us extend the NewChip1 code from
previous section. Here we add a waveguide from a launcher to a capacitor
using refpoints::

    # In addition to the imports from previous example, import these:
    from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
    from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare


    class NewChip1(Chip):

        def build(self):

            # After produce_launchers call, there will be "chip-level" refpoints in self.refpoints.
            # These refpoints have prefixes corresponding to launcher names, such as "WN" for one
            # of the SMA8 launchers. Same is true for elements inserted with an inst_name.
            self.produce_launchers("SMA8")

            # ... other code here ...

            # insert_cell can return a dictionary of refpoints for the inserted element
            _, cap_refpoints = self.insert_cell(FingerCapacitorSquare, pya.DTrans(1, False, 5000, 3000))
            # Refpoints can be used to position WaveguideCoplanar path points or WaveguideComposite nodes.
            self.insert_cell(
                WaveguideCoplanar,
                path=pya.DPath([
                    # "Chip-level" refpoints with launcher name prefix "WN"
                    self.refpoints["WN_port"],
                    self.refpoints["WN_port_corner"],
                    # Refpoints of the capacitor element instance (no instance name prefix)
                    cap_refpoints["port_b_corner"],
                    cap_refpoints["port_b"],
                ], 0),
            )


How to use the points once they exist? Several styles have evolved:

- Just use them as a point and perhaps do some geometry calculations to come up with other points
  relative to it. This style is mostly useful inside element code, since that is the part of the code
  where the geometry is being implemented anyway.
- When composing elements in a chip or element, you can use ``align`` and ``align_to`` arguments of
  ``insert_cell()``. These can be either a point or a string name referring to a refpoint name, and
  will displace (but not rotate!) the element such that the two points overlap. For example::

   self.insert_cell(SomeElement, align="refpoint_of_some_element", align_to=self.refpoints["existing_ref"])


Refpoints are not visible by default in KLayout. Enable the ``texts/refpoints`` layer to see all
refpoints. If there are many overlapping refpoints the texts can be hard to read. In this case, the
``texts/top refpoints`` layer may be used to see only the top-level refpoints. For this choose a new
top cell by right clicking the chip in the cell view of KLayout and selecting "Show As New Top".
This can be very useful to see "chip-level" refpoints only.

Port refpoints
--------------

In KQCircuits, many elements are designed to connect together with waveguides. To ensure waveguides can be connected
correctly, define a port with position and direction using :func:`Element.add_port`::

   self.add_port(name, position, direction)

This creates a pair of refpoints with the naming convention:

- ``port_name`` at the position where the waveguide should attach
- ``port_name_corner`` which is one waveguide corner radius (parameter ``r``) away in the direction where the
  waveguide should go.

To connect a waveguide to a port, route it from ``something_port`` to ``something_port_corner``, and then
wherever you want to go (this works up to 90 degree turns).

The :class:`.WaveguideComposite` element can insert arbitrary elements inside waveguides, and connect them correctly
as long as the element has at least two ports defined.

.. note::
   ``add_port`` also adds a point in the ``ports`` layer of the given face. These points are used by
   :mod:`kqcircuits.util.netlist_extraction` to detect how elements are connected.
