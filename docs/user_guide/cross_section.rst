.. _cross_sections:

Cross sections
**************

It is possible to generate vertical cross section geometries from an arbitrary KQC layout,
by specifying two points that form a line from which a cross-section is formed.
Following are the ways to generate a cross section.

Creating cross sections with KQCircuits
=======================================

In GUI
------

There is currently no convenient way to create cross sections using this method in KLayout GUI,
therefore its better to use the XSection tool for this purpose.

In KQC code
-----------

:git_url:`klayout_package/python/kqcircuits/simulations/export/cross_section/cross_section_export.py` includes
a ``create_cross_sections_from_simulations`` function. Given list of ``Simulation`` instances and two ``DPoint``
values, a list of ``CrossSectionSimulation`` objects will be created to a separate layout. See
:git_url:`klayout_package/python/scripts/simulations/waveguides_sim_cross_section.py` for an example use case.

Cross sections are an essential part in calculating EPR for elements. See docstring in
:git_url:`klayout_package/python/kqcircuits/simulations/export/cross_section/epr_correction_export.py`
and :git_url:`klayout_package/python/scripts/simulations/swissmon_epr_sim.py` for an example use case.

XSection tool
=============

XSection tool is an external plug-in developed by KLayout developer.
To use it, install the XSection plugin from ``KLayout -> Tools -> Manage packages``.

KLayout GUI XSection tool
-------------------------

Once XSection plugin is installed in KLayout, a "XSection" ruler tool is available
as a scroll option for the Ruler tool.

   1. Use the "XSection" Ruler tool in KLayout to choose the cuts along which the vertical
      cross-sections are created

   2. ``Tools -> XSection scripts -> Run script -> example.xs`` will open another layout
      displaying the cross section geometry.

XSection call in KQC code
-------------------------

.. warning::
   The use of XSection tool within KQCircuits code is deprecated, it is recommended
   to use internal KQCircuits utilities instead to generate cross sections

XSection plugin can be called from python code to automate cross-section geometry
generation for simulation files.
:git_url:`klayout_package/python/kqcircuits/simulations/export/cross_section/xsection_export.py` includes

   -  ``create_xsections_from_simulations``, a high level method to take a cross-section
      for each simulation object using two ``DPoint`` values

   -  ``xsection_call``, a low level method requiring a path to the input and output
      OAS files, two ``DPoint`` values and, optionally, a path to a process file.
      If :git_url:`xsection/kqc_process.xs` process file is used, make sure to
      provide a path to the parameters json file as well.

.. note::
   XSection 1.7 does not work with KQCircuits. If you have such version installed, please
   update to the newest release of XSection.

Process files (.xs)
-------------------

The process by which the actual physical shapes are created from the layout
layers is defined in ``.xs`` files. The xsection folder in KQC contains two
process files:

   1. Lightweight example process file :git_url:`xsection/example.xs`, intended for taking cross-sections
      using a KLayout GUI tool

   2. **(deprecated)** :git_url:`xsection/kqc_process.xs` intended only for use by a ``create_xsections_from_simulations``
      call in KQC code

Information about writing the ``.xs`` files can be found in the following pages:

- https://klayoutmatthias.github.io/xsection/DocIntro
- https://klayoutmatthias.github.io/xsection/DocReference
- https://klayoutmatthias.github.io/xsection/DocGrow
- https://klayoutmatthias.github.io/xsection/DocEtch
