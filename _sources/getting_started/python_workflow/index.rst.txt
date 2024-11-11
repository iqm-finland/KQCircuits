Python workflow
===============

The main way of working in KQCircuits is to define elements and chips as python code. This gets the most out of
KQCircuits features, creating maintainable and parametrized designs.

In this section, we introduce the code-based workflow and structure of KQCircuits step by step.

.. note::
   In the getting started documentation, we show code that can be used in the ``build`` function of elements and chips.
   Most of the same features can also be used in Simulation classes (see :ref:`simulation_object`) to define
   electromagnetic field simulations, and in KLayout macros or standalone python scripts to generate geometry
   independent of chips (see :ref:`macro_workflow`)

.. toctree::
   :maxdepth: 1

   python_start
   python_structure
   python_example
   refpoints
   layers
   faces