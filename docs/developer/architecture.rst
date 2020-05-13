Architecture
------------

This section explains some things about the KQCircuits code architecture.

Elements
^^^^^^^^

.. image:: ../images/class_diagram_1.png
    :alt: class diagram

Every KQCircuits object that can be placed in a KLayout layout is either an
``Element``, a ``Chip``, or a ``TestStructure``. Both ``Chip`` and
``TestStructure`` inherit from ``Element``. Elements in KQCircuits are PCells
(see `KLayout documentation <https://www.klayout
.de/doc-qt5/about/about_pcells.html>`__ for more information on PCells), or
more specifically, they inherit from `PCellDeclarationHelper <https://www
.klayout.de/doc-qt4/code/class_PCellDeclarationHelper.html>`__. Due to how
KLayout handles PCells, the elements (i.e. classes inheriting from Element) in
KQCircuits should not be treated as normal Python classes. The following
things should be taken into account when writing new elements:

#.  PCells in Python code have corresponding objects living in the C++-side of
    KLayout. This means that you should not instantiate any elements like a
    normal class, but instead use the ``create_cell`` method of the element,
    which is a wrapper for KLayout's ``layout.create_cell()``. This wrapper is
    used to validate the parameters using the ``Validator`` in
    ``parameter_helper.py`` . The C++-object is created properly only if you use
    ``create_cell`` (or if a new PCell is added to a layout in KLayout GUI).

#.  When a new PCell instance is created using ``create_cell`` or in KLayout
    GUI, or when the parameters are changed in KLayout GUI, the ``produce_impl``
    method of the PCell is called. This method is where you "build" the
    PCell. When ``produce_impl`` is called, the  instance variables of the
    PCell are set to new values based on the given parameters. The PCell
    instance is then created or updated based on these new parameter values.

#.  The PCell parameters for KQCircuits elements are given as a dictionary
    named ``PARAMETER_SCHEMA``, which should exist in the class of every
    element. The values of these parameters can be set from the KLayout GUI,
    or in the ``create_cell`` method in code. For each parameter in
    ``PARAMETER_SCHEMA``, there will automatically be created an instance
    variable with the same name. The ``PARAMETER_SCHEMA`` of a class is
    automatically merged with its parent's ``PARAMETER_SCHEMA`` (see
    ``element.py``), so the class will contain the parameters of all its
    ancestors in the inheritance hierarchy .

Libraries
^^^^^^^^^

The PCells in KQCircuits are divided into the libraries ``elements``, ``chips``
and ``test_structures``. Each library contains a base class for all other
classes in the library, for example all classes in ``chips`` library
inherit from ``Chip``. The base class contains ``LIBRARY_NAME`` and
``LIBRARY_DESCRIPTION``, so that these are available for all elements.

The elements in these libraries are automatically discovered and registered to
KLayout by ``library_helper.py``. It finds all classes in KQCircuits
directory which inherit from ``PCellDeclarationHelper``, and uses their
``LIBRARY_NAME`` attribute to register them to the correct library. Note
that this requires all element classes to follow PascalCase naming
convention, as required by PEP-8.

pya resolver
^^^^^^^^^^^^

Any KLayout functions/classes/etc. should be imported using ``pya_resolver``
(see ``pya_resolver.py``). For example, you should write
``from kqcircuits.pya_resolver import pya``, and **not** ``import pya`` or
``import klayout.db``. This ensures that KQCircuits works both with KLayout
GUI and the standalone module.