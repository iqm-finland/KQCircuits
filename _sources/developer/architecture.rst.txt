Architecture
------------

This section explains some things about the KQCircuits code architecture.

.. _architecture_elements:

Elements
^^^^^^^^

.. image:: ../images/class_diagram_1.png
    :alt: class diagram

Every KQCircuits object that can be placed in a KLayout layout is derived from
``Element``. There exist also more specific base classes such as ``Chip``,
or ``TestStructure``, which inherit from ``Element``. Elements in KQCircuits
are PCells (see `KLayout documentation <https://www.klayout
.de/doc-qt5/about/about_pcells.html>`__ for more information on PCells), or
more specifically, they inherit from `PCellDeclarationHelper <https://www
.klayout.de/doc-qt4/code/class_PCellDeclarationHelper.html>`__. Due to how
KLayout handles PCells, the elements (i.e. classes inheriting from Element) in
KQCircuits should not be treated as normal Python classes. The following
things should be taken into account when writing new elements:

#.  PCells in Python code have corresponding objects living in the C++-side of
    KLayout. This means that you should not instantiate any elements like a
    normal class, but instead use the ``add_element`` or ``create`` method of the
    element, which are wrappers for KLayout's ``layout.create_cell``.  These
    wrappers are used to validate the parameters using the ``Validator`` in
    ``parameter_helper.py``. The C++-object is created properly only if you use
    these wrappers (or if a new PCell is added to a layout in KLayout GUI).

#.  In code ``add_element`` or ``insert_cell`` is the preferred method of adding
    a new (sub)cell. The ``create`` method is a ``@classmethod`` that is useful
    when adding a top level PCell or when not calling from another PCell.

#.  When a new PCell instance is created, or when the parameters are changed in
    KLayout GUI, the ``produce_impl`` method of the PCell is called. For KQC
    elements ``produce_impl`` calls the ``build`` method, which is where you
    "build" the element. When ``produce_impl`` is called, the instance variables
    of the PCell are set to new values based on the given parameters. The PCell
    instance is then created or updated based on these new parameter values.

.. _architecture_parameters:

PCell parameters
^^^^^^^^^^^^^^^^

The PCell parameters for KQCircuits elements are plain class attributes defined
with the ``Param`` descriptor class. These can be used like normal instance
variables. The values of these parameters can be set from the KLayout GUI, or in
the ``create`` or ``add_element`` methods in code.  The parameters of a class
are automatically merged with its parent's parameters (see ``element.py``), so
an instance will contain the parameters of all its ancestors in the inheritance
hierarchy. When building hierarchical elements the parameter values appropriate
for a sub-element are transparently passed to it from the caller with
``add_element`` or ``insert_cell``.

It is possible to change inherited parameters default values in a per class
basis using the ``default_parameter_values`` section of the ``defaults.py``
configuration file. Technically this creates a copy of the Param object with
different default value.

The ``add_parameters_from`` decorator function adds some other class'
parameter(s) to the decorated class so there is no need to re-define the same
parameter in multiple places. They are like normal parameters to all intents and
purposes. Note that these parameters will be inherited by descendants of the
decorated class. Technically these are like references to the same Param object.

With ``add_parameters_from`` it is also possible to add some other class'
parameter with a changed default value. This is practically identical to setting
a default value for the decorated class using ``default_parameter_values`` in
the configuration file.

Examples::

    # Get two parameters form 'OtherClass'
    @add_parameters_from(OtherClass, "param_a", "param_b")
    class MyClass():

    # Get all parameters form 'OtherClass'
    @add_parameters_from(OtherClass, "*")  # or just @add_parameters_from(OtherClass)
    class MyClass():

    # Get all parameters form 'OtherClass' except one
    @add_parameters_from(OtherClass, "*", "param_a")
    class MyClass():

    # Get and change default values of several parameters at once
    @add_parameters_from(OtherClass, "param_a", "param_b", param_c=42, param_d=43)
    class MyClass():

    # Get all parameters form 'OtherClass' but override one
    @add_parameters_from(OtherClass, "*", param_b=41)
    class MyClass():

Note that decorators are applied in "reverse-order", i.e. first the class is
defined and then from bottom-up the decorators are called. This is also the
reason why decorators may override Param definitions in the class' body but not
the other way around.

Libraries
^^^^^^^^^

The PCells in KQCircuits are divided into libraries such as ``elements``,
``chips`` and ``test_structures``. Each library contains a base class for all
other classes in the library, for example all classes in ``chips`` library
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
