Mask export
===========

Masks are defined by simple scripts, which define the layout of chips in the
mask and the parameters of those chips. These scripts will export
``.oas``/``.gds`` files required for photomask production and possibly EBL,
as well as auxiliary files such as netlists, images and automatic mask
documentation. The mask scripts can be run either from the macro editor or
from the command line using ``klayout -z -r ./scripts/masks/maskname.py``.

Tutorial
--------

Basic mask script and export
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    #. Launch KLayout Editor and open the Macro IDE (F5).

    #. Add the following script to the `kqcircuits_scripts/masks <https://github.com/iqm-finland/KQCircuits/tree/main/klayout_package/python/scripts/masks>`_ folder in
       the ``Python`` tab of the Macro IDE::

        # Imports required for any mask
        from kqcircuits.defaults import TMP_PATH
        from kqcircuits.masks.mask_set import MaskSet
        from kqcircuits.klayout_view import KLayoutView
        # Import chips required for this mask
        from kqcircuits.chips.demo import Demo

        # Get current view and layout
        view = KLayoutView(current=True, initialize=True)
        layout = KLayoutView.get_active_layout()

        # Initialize mask object.
        # "name" and "version" will be displayed in labels inside the mask
        # and in the names of the exported files.
        # "with_grid" determines if the ground plane grid is created.
        test_mask = MaskSet(layout, name="Test", version=1, with_grid=False)

        # Add mask layouts.
        # A mask layout determines which chip is at each position. The chips are
        # identified by strings which are defined by the `add_chip()` calls
        # below. "---" denotes places without a chip.
        test_mask.add_mask_layout([
            ["---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---"],
            ["---", "---", "---", "---", "---", "DE1", "DE1", "DE1", "DE1", "DE1", "---", "---", "---", "---", "---"],
            ["---", "---", "---", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "---", "---", "---"],
            ["---", "---", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "---", "---"],
            ["---", "---", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "---", "---"],
            ["---", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "---"],
            ["---", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "---"],
            ["---", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "---"],
            ["---", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "---"],
            ["---", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "---"],
            ["---", "---", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "---", "---"],
            ["---", "---", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "---", "---"],
            ["---", "---", "---", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "---", "---", "---"],
            ["---", "---", "---", "---", "---", "DE1", "DE1", "DE1", "DE1", "DE1", "---", "---", "---", "---", "---"],
            ["---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---"],
        ])

        # Chip definitions
        test_mask.add_chip(Demo, "DE1")

        # Build the mask.
        # This generates the layout in KLayout based on previous calls to
        # ``add_mask_layout()`` and ``add_chip()`.
        test_mask.build()
        # Export the mask files to TMP_PATH
        test_mask.export(TMP_PATH, view)

       Any mask script should follow roughly the same structure. The
       beginning and end of the script (getting the view, and exporting the
       mask) are generally the same for any mask.

    #. (Optional) Open `kqcircuits_scripts/macros/logging_setup <https://github.com/iqm-finland/KQCircuits/blob/main/klayout_package/python/scripts/macros/logging_setup.lym>`_ and run it.
       This makes mask generation logs visible in the Macro console.

    #. With the mask script open, click "Run script from current tab"
       (Shift+F5). This generates the mask and exports the files to the
       folder defined by ``kqcircuits.default.TMP_PATH``.

If you generate the mask again (for example in the following sections), it is
recommended that you first close the layout where the previous mask was
generated.

Ground grid
^^^^^^^^^^^

The generated masks can include a ground plane grid, which automatically
avoids other elements. To generate it, use ``with_grid=True`` in the mask object
initialization::

    test_mask = MaskSet(layout, name="Test", version=1, with_grid=True)

Because the grid generation is slow, it is recommended to keep
``with_grid=False`` when testing masks, and only use ``with_grid=True`` for
masks that are really produced.

Adding and modifying chips
^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Add the following lines to the imports section of the script::

    from kqcircuits.chips.multi_face.demo_twoface import DemoTwoface
    from kqcircuits.chips.quality_factor import QualityFactor

#. Add the new chips::

    test_mask.add_chip(DemoTwoface, "DT1")
    test_mask.add_chip(QualityFactor, "QF1")

#. Add a new variant of the demo chip with different parameters::

    test_mask.add_chip(Demo, "DE2", include_couplers=False, readout_res_lengths=[5400, 5500, 5600, 5700])

#. Replace some of the "DE1" entries in the mask layout by "DT1", "QF1" and
   "DE2". This will determine where those chips are placed in the mask.

#. Generate the mask. You should see the new chip variants at the positions
   defined in the previous step.

Multi-face masks
^^^^^^^^^^^^^^^^

The mask generated in the previous step contained "DemoTwoface" chips, which
are supposed to have elements in two different chip faces for a flip-chip
process. However, the generated mask only contained the parts in "bottom"
face. To generate mask for also "top"-face chips, we need to add an
additional `mask_layout <https://github.com/iqm-finland/KQCircuits/blob/main/klayout_package/python/kqcircuits/masks/mask_layout.py>`_

#. Add the following below the old ``add_mask_layout()`` call::

    test_mask.add_mask_layout([
        ["---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---"],
        ["---", "---", "---", "---", "---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---", "---", "---", "---", "---"],
        ["---", "---", "---", "---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---", "---", "---", "---"],
        ["---", "---", "---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---", "---", "---"],
        ["---", "---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---", "---"],
        ["---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---"],
        ["---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
        ["---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
        ["---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
        ["---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
        ["---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
        ["---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
        ["---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
        ["---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
        ["---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
        ["---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---"],
        ["---", "---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---", "---"],
        ["---", "---", "---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---", "---", "---"],
        ["---", "---", "---", "---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---", "---", "---", "---"],
        ["---", "---", "---", "---", "---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---", "---", "---", "---", "---"],
        ["---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---"],
    ], "t")

   Notice the "t" argument after the actual mask layout. This means that only
   elements which are in chip face "t" will be included in this mask layout.
   By default, the mask layout will use elements in chip face "b", which is
   the case for the first mask layout in this script.

#. Generate the mask. In KLayout cell hierarchy, you should see both "Test b"
   and "Test t" cells. You can right click them and select "Show as new
   top" to verify that "Test b" contains the parts of DemoTwoface in "b"-face
   and "Test t" contains the parts of DemoTwoface in "t"-face (with proper
   mirroring and rotation).
