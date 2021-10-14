Python workflow tutorial
========================

This is a collection of tips and tricks about the "Python workflow".

To unlock the full potential of KQCircuits the user often needs to define new Chips and Elements,
which is done by writing Python code. This can be done in the Macro Editor included in KLayout, or
using any external code editor. To start working with the KQCircuits code base directly, see
:ref:`developer_setup`.

File system hierarchy
---------------------

TODO: describe where the different parts of KQCircuits are located in the file system.

Structure of  PCell code
------------------------

TODO: describe the general structure of PCell code, Element class, parameters, produce_impl(), etc.

Example of defining a Chip and an Element
-----------------------------------------

TODO: further details about writing Element and Chip code.

Example of inserting an Element
-------------------------------

TODO: how to bild new Elements or Chips from existing Elements.

Refpoints
---------

In an Element definition ``refpoints`` is just a dictionary of points. You can add to it by
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

How to use the points once they exist? Several styles have evolved:

- Just use them as a point and perhaps do some geometry calculations to come up with other points
  relative to it. This style is mostly useful inside element code, since it is there you really need
  to decide on geometry.
- On the Chip or Simulation level you can use ``align`` and ``align_to`` arguments of
  ``insert_cell()``. These can be either a point or a string name referring to a refpoint name, and
  will displace (but not not rotate!) the element such that the two points overlap. For example,
  ``insert_cell(SomeElement, align="refpoint_of_some_element",
  align_to=self.refpoints["existing_ref"])``.

There is a convention followed almost everywhere: Places where you normally connect coplanar
waveguides have a refpoint named ``something_port`` and a second refpoint ``something_port_corner``
which is one corner-radius (``r``) away and indicates the direction that the connecting waveguide
should go. You can connect a waveguide correctly by routing it from ``something_port`` to
``something_port_corner``, and then wherever you want to go (can't do more than 90 degree turns this
way!). This point is also useful in simulations to pass to ``produce_waveguide_to_port()``.

The `WaveguideComposite
<../api/kqcircuits.elements.waveguide_composite.html#kqcircuits.elements.waveguide_composite.WaveguideComposite>`_
element has some logic where you can insert arbitrary elements inside waveguides and it uses these
points to align and connect them correctly.

Refpoints are not visible by default in KLayout. Enable the ``texts/refpoints`` layer to see all
refpoints. If there are many overlapping refpoints the texts can be hard to read. In this case, the
``texts/top refpoints`` layer may be used to see only the top-level refpoints. For this choose a new
top cell by right clicking the chip in the cell view of KLayout and selecting "Show As New Top".
This can be very useful to see "chip-level" refpoints only.
