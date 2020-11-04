"""PCell declaration classes for elements.

Elements represent all the different structures that form a quantum circuit. They are implemented as PCells, with the
base class of ELement being PCellDeclarationHelper. After loading elements into KLayout PCell libraries, they can be
placed in a layout using the KLayout GUI or in code.

Elements contain some shared PCell parameters, including a list of refpoints which can be used to position them. They
also have methods that make it easy to create elements with different parameters and insert them to other elements.

Elements support a concept of faces, which is used for 3D-integrated chips to place shapes in layers belonging to a
certain chip face. For example, an element may create shapes in face 0 and face 1, and the ``face_ids`` parameter
of the element determines which actual chip faces the faces 0 and 1 refer to.
"""