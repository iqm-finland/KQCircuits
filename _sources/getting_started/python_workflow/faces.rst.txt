Faces
=====

KQCircuit layers are grouped by faces and functionality. A chip's "face" intuitively means the
bottom or top sides of it. To identify faces in multi chip configurations we number the chips from
"1". For technical reasons we permit multiple faces in a particular side. For example "2b1" denotes
the bottom face of the 2nd chip in a typical flip-chip configuration.

The example chips included in KQCircuits use up to four faces, describing a flip-chip architecture. Face `1t1` is the
bottom chip, and also the face used for single-face designs. `2b1` is the bottom side of the top chip, connecting to
`1t1` with indium bumps. See the :class:`DemoTwoface` chip for an example flip-chip design. The faces `1b1` and `2t1`
(representing the outer side of

.. note::
  The face configuration is defined in
  :git_url:`default_layer_config.py <klayout_package/python/kqcircuits/layer_config/default_layer_config.py>`. To learn
  about defining a custom configuration for different stackups, see :ref:`face_configuration`.

Using faces
-----------

All KQC elements have a parameter ``face_ids``, which is a list of the faces available to that element. When drawing
geometry, the element should not use face_id strings directly, but use indices to ``self.face_ids``. This way,
each element can be placed on any face, simply by giving it the appropriate order of faces in ``face_ids``.

Simple KQC elements draw geometry only on a single face, which is always the first face in ``face_ids``. However,
many elements (such as connectors, indium bumps, and TSVs) span multiple faces, and they use these faces based on
the order they appear in ``face_ids``, as shown in the examples below.

By default, ``face_ids=["1t1", "2b1", "1b1", "2t1"]`` for all elements, and this is the order used when dragging an
element from the library in the KLayout GUI.

Creating shapes in faces
^^^^^^^^^^^^^^^^^^^^^^^^

The function :func:`Element.get_layer` returns the correct layer for a face. By default, face 0 is used, i.e. the first
face in ``face_ids``. To draw in other faces, pass the index of the face to draw in::

    # (the face_id passed to self.get_layer is actually an index to self.face_ids)
    self.cell.shapes(self.get_layer("indium_bump", face_id=0)).insert(pya.DBox(0, 500, 500, 0))
    self.cell.shapes(self.get_layer("indium_bump", face_id=1)).insert(pya.DBox(100, 400, 400, 100))

In this example, if ``self.face_ids==["1t1", "2b1"]``, the first shape is draw in in `1t1_indium_bump`, and the second
in `2b1_indium_bump`.

Placing elements on faces
^^^^^^^^^^^^^^^^^^^^^^^^^

When inserting a child element in multi-face chips or elements, pass a re-ordered list or subset of ``self.face_ids``
to place the element on the desired faces.

For example, in a chip with ``self.face_ids==["1t1", "2b1"]``, an element can be placed on `2b1` as follows::

    # Placing a single-face element in a different face than the default
    self.insert_cell(Launcher, face_ids=[self.face_ids[1]])

For an element that spans multiple faces, one often changes the order of face ids::

    # Placing a multi-face element with the parts in different faces swapped
    self.insert_cell(FlipChipConnectorRf, face_ids=[self.face_ids[1], self.face_ids[0]])
