Creating cross section images
=============================

Vertical cross-section images of layouts can be created using the
`XSection plugin <https://klayoutmatthias.github.io/xsection/>`_ for KLayout.
The process by which the actual physical shapes are created from the layout
layers is defined in ``.xs`` files. The xsection folder in KQC contains an
example ``example.xs``.

To use it, do the following:

1. Install XSection from ``KLayout -> Tools -> Manage packages``.
2. Use the Ruler tool in KLayout to choose the cuts along which the vertical
   cross-sections are created. Select the "XSection" ruler type if you want to
   use other rulers for measurements.
3. To create the cross-sections: ``Tools -> XSection scripts -> Run script ->
   example.xs``

Information about writing the ``.xs`` files can be found in the following pages:

- https://klayoutmatthias.github.io/xsection/DocIntro
- https://klayoutmatthias.github.io/xsection/DocReference
- https://klayoutmatthias.github.io/xsection/DocGrow
- https://klayoutmatthias.github.io/xsection/DocEtch

