.. _python_structure:

Structure of Element code
=========================

This section discusses the main structure Elements in more detail

``Element`` class
-----------------

Any KQCircuits Elements must be derived from the :class:`.Element` class, and we
call them "elements". For example, to define a new element ``MyElement`` you
would start the code with::

    class MyElement(Element):

You can of course also have elements derived from other existing elements
instead of Element directly::

    class MyElement2(MyElement):

KQCircuit Elements are based on KLayout PCells. KQCircuits features make it easier to define and place elements, use
a refpoint system to position and connect elements together, and the concept of chip faces to easily create multilayer
designs with flip chip or through-silicon vias (TSVs).

Libraries
---------

There are separate libraries in KQCircuits for certain kinds of elements, such as qubits or chips. To add your element
into a specific library, it must be put in the corresponding subfolder (or its subfolders) of the
``kqcircuits`` folder (or user package folder) and it must be a child class of the corresponding base
class. For example, to define a new qubit in the "Qubit library", you would need to have::

    class MyQubit(Qubit):

in a file ``my_qubit.py`` in the ``qubits`` folder.

.. _python_workflow_parameters:

Parameters
----------

Different element instances with varying features can be created by setting different parameters.
Parameters can be modified in GUI or when creating the instance in code.
The parameters of a KQCircuits element are defined using ``Param``
objects as class-level variables, for example::

    bridge_length = Param(pdt.TypeDouble, "Bridge length (from pad to pad)", 44, unit="μm")

The ``Param`` definition always has type, description and default value, and
optionally some other information such as the unit or ``hidden=True`` to hide
it from GUI. More information about parameters can be found in
:ref:`architecture_parameters` section.

Build
-----

The geometry for any KQCircuit element is created in the ``build`` method, so
generally you should define at least that method in your element classes, as shown in the examples in the follwing
sections.

.. tip::
   A detailed discussion of the KQCircuits architecture can be found in the :ref:`Developer guide <architecture_elements>`.
