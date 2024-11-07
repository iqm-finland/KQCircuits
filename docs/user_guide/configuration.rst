Custom configuration
====================

.. _configure_sample_holders:

Configuring sample holders
--------------------------

The available sample holder types are  defined in :git_url:`defaults.py <klayout_package/python/kqcircuits/defaults.py>`
``default_sampleholders``. Each sample sample holder type is a dictionary of parameters specifying the launcher
placement, and the appropriate chip size.

You can add new sampleholder types by extending the dictionary, for example::

    "RF16": {
        "n": 16,
        "launcher_type": "RF",
        "launcher_width": 400,
        "launcher_gap": 150,
        "launcher_indent": 1000,
        "pad_pitch": 2000,
        "chip_box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(12000, 12000))
    }

This can then be used in a chip::

    self.produce_launchers("RF16")

A quick way to view all available sampleholder types is to use the
:class:`.Launchers` chip and change its ``sampleholder_type`` parameter.


.. _face_configuration:

Configuring faces
-----------------

Layer configuration files
^^^^^^^^^^^^^^^^^^^^^^^^^

Layer configuration files are used to define the names of layers and faces, and
many other values related to them. The ``layer_config_path`` variable in
:git_url:`defaults.py <klayout_package/python/kqcircuits/defaults.py>`
controls which layer configuration file is used, so you can define your own
layer configuration with completely different layer names etc. and use it by
changing ``layer_config_path``.

For more information on what to include in these layer configuration files, see
the comments in :git_url:`defaults.py <klayout_package/python/kqcircuits/defaults.py>`
and the layer configuration files in
:git_url:`layer_config <klayout_package/python/kqcircuits/layer_config>`
directory. Currently included are
:git_url:`default_layer_config.py <klayout_package/python/kqcircuits/layer_config/default_layer_config.py>`
(used by default in KQC) and a simpler
:git_url:`example_layer_config.py <klayout_package/python/kqcircuits/layer_config/example_layer_config.py>`
which may be useful as a starting point to define your own layer
configuration file.


Adding a new face
^^^^^^^^^^^^^^^^^

New layers and new faces can be added in
:git_url:`defaults.py <klayout_package/python/kqcircuits/defaults.py>`
by modifying ``default_layers`` and ``default_faces``. As an example, let's
add a new face ``x`` with some layers that are in KQCircuits default faces
and one new layer::

    default_layers["x_base_metal_gap_wo_grid"] = pya.LayerInfo(130, 9, "x_base_metal_gap_wo_grid")
    default_layers["x_ground_grid_avoidance"] = pya.LayerInfo(133, 9, "x_ground_grid_avoidance")
    default_layers["x_ports"] = pya.LayerInfo(154, 9, "x_ports")
    default_layers["x_new_layer"] = pya.LayerInfo(999, 9, "x_new_layer")

    default_faces["x"] = {
        "id": "x",
        "base_metal_gap_wo_grid": default_layers["x_base_metal_gap_wo_grid"],
        "ground_grid_avoidance": default_layers["x_ground_grid_avoidance"],
        "ports": default_layers["x_ports"],
        "new_layer": default_layers["x_new_layer"],
    }

The layers are identified by ``layer number``, ``data type`` and ``name``,
e.g. ``900``, ``1`` and ``x_base_metal_gap_wo_grid``

These lines should be added after the last line where ``default_layers`` or
``default_faces`` are modified. It is best to do these changes in the layer
configuration file (see previous section), although it can also be done in
`defaults.py` directly. Launching KLayout after these changes, you
should see the new layers in the layers list. If you add for example
:class:`.Launcher` element to the layout and modify its ``face_ids``
parameter to have the value ``x``, it will then use the layers from the newly
added face ``x``.

To change the color of the layers and their organization in the layers list,
the layer properties file (determined by ``default_layer_props`` in the layer
configuration file) must be modified or another layer properties file must be
set as default in KLayout Setup menu. The layer properties file can be edited
directly or by modifying the layers list in GUI and saving them using KLayout
``File -> Save Layer Properties``.
