Creating cross section images
=============================

Vertical cross-section images of layouts can be created using the
`XSection plugin <https://klayoutmatthias.github.io/xsection/>`_ for KLayout.
To use it, install the XSection plugin from ``KLayout -> Tools -> Manage packages``.

KLayout GUI XSection tool
-------------------------

Once XSection plugin is installed in KLayout, a "XSection" ruler tool is available
as a scroll option for the Ruler tool.

   1. Use the Ruler tool in KLayout to choose the cuts along which the vertical
      cross-sections are created. Select the "XSection" ruler type if you want to
      use other rulers for measurements.

   2. To create the cross-sections: ``Tools -> XSection scripts -> Run script ->
      example.xs``

XSection call in KQC code
-------------------------

XSection plugin can be called from python code to automate cross-section geometry
generation for simulation files.
:git_url:`klayout_package/python/kqcircuits/export/xsection_export.py` includes

   -  ``create_xsections_from_simulations``, a high level method to take a cross-section
      for each simulation object using two ``DPoint`` values

   -  ``xsection_call``, a low level method requiring a path to the input and output
      OAS files, two ``DPoint`` values and, optionally, a path to a process file

An example of using XSection tool to produce cross-section simulation files is
demonstrated in :git_url:`klayout_package/python/scripts/simulations/waveguides_sim_xsection.py`

Process files (.xs)
-------------------

The process by which the actual physical shapes are created from the layout
layers is defined in ``.xs`` files. The xsection folder in KQC contains two
process files:

   1. Lightweight example process file :git_url:`xsection/example.xs`, intended for taking cross-sections
      using a KLayout GUI tool

   2. :git_url:`xsection/kqc_process.xs` intended only for use by a ``create_xsections_from_simulations``
      call in KQC code

Information about writing the ``.xs`` files can be found in the following pages:

- https://klayoutmatthias.github.io/xsection/DocIntro
- https://klayoutmatthias.github.io/xsection/DocReference
- https://klayoutmatthias.github.io/xsection/DocGrow
- https://klayoutmatthias.github.io/xsection/DocEtch

