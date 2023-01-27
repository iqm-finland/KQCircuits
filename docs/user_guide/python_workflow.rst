Python workflow tutorial
========================

This is a collection of tips and tricks about the "Python workflow".

To unlock the full potential of KQCircuits the user often needs to define new Chips and Elements,
which is done by writing Python code. This can be done in the Macro Editor included in KLayout, or
using any external code editor. To start working with the KQCircuits code base directly, see
:ref:`developer_setup`. In addition to KQCircuits documentation it is useful
to check the `KLayout documentation <https://www.klayout.de/doc.html>`__ when
writing Python code for new elements.

File system hierarchy
---------------------

In the KQCircuits root folder the most important folder for most users is the
:git_url:`klayout_package` folder, which is also all that is included in the Salt
package. Other folders are mainly for automatic tests and documentation.
KQCircuits code is divided into the :git_url:`kqcircuits <klayout_package/python/kqcircuits>` and
:git_url:`scripts <klayout_package/python/scripts>` folders in :git_url:`klayout_package/python`.
These two folders are also (after installation process) linked as symbolic links ``kqcircuits`` and
``kqcircuits_scripts`` in the ``~/.klayout`` or ``~/KLayout`` folder.

The ``kqcircuits`` folder contains all the KQCircuits PCell classes and many
other modules used by them or by scripts. Folders directly under under
``kqcircuits`` containing PCell classes correspond to different PCell
libraries such as elements, chips, or test structures.

The ``scripts`` folder contains macros to be run in KLayout GUI and
scripts for generating simulation files or mask files. The files there are in
general not meant to be imported in other Python files. The outputs of
simulation or mask scripts can be found in the ``tmp`` folder below the main
KQCircuits folder.

Structure of  PCell code
------------------------

:class:`.Element` class
^^^^^^^^^^^^^^^^^^^^^^^

Any KQCircuits PCells must be derived from the :class:`.Element` class, and we
call them "elements". For example, to define a new element ``MyElement`` you
would start the code with::

    class MyElement(Element):

You can of course also have elements derived from other existing elements
instead of Element directly::

    class MyElement2(MyElement):

The KQCircuits Element class offers many useful features compared to normal
KLayout PCells. These features include helper functions for inserting subcells
and for using layers, a refpoint system for positioning elements, nicer
parameter syntax, automatic loading into a pcell library, and more.
Further details about the code architecture of KQCircuits elements can be
found in :ref:`architecture_elements`.

PCell Libraries
^^^^^^^^^^^^^^^

There are separate PCell libraries in KQCircuits for certain kinds of
elements, such as qubits or chips. To add your element into a specific
library, it must be put in the corresponding subfolder (or its subfolders) in
``kqcircuits`` folder and it must be a child class of the corresponding base
class. For example, to define a new qubit in the "Qubit library", you would
need to have::

    class MyQubit(Qubit):

in a file ``my_qubit.py`` in ``kqcircuits/qubits`` folder. The registration
of PCell classes to different libraries is handled by KQCircuits code in
:git_url:`library_helper.py <klayout_package/python/kqcircuits/util/library_helper.py>` and :git_url:`element.py
<klayout_package/python/kqcircuits/elements/element.py>`. For more information about PCell libraries see the KLayout
documentation pages
https://www.klayout.de/doc-qt5/about/about_libraries.html,
https://www.klayout.de/doc-qt5/code/class_Library.html, and
https://www.klayout.de/doc-qt5/programming/ruby_pcells.html#h2-426 (in Ruby).


Parameters
^^^^^^^^^^

PCell parameters are used to create PCell instances with different parameter
values. They can be modified in GUI or when creating the instance in code.
The PCell parameters of a KQCircuits element are defined using ``Param``
objects as class-level variables, for example::

    bridge_length = Param(pdt.TypeDouble, "Bridge length (from pad to pad)", 44, unit="μm")

The ``Param``  definition always has type, description and default value, and
optionally some other information such as the unit or ``hidden=True`` to hide
it from GUI. More information about parameters can be found in
:ref:`architecture_parameters` section.

Build
^^^^^

The geometry for any KQCircuit element is created in the ``build`` method, so
generally you should define at least that method in you element classes. See
:ref:`architecture_elements` section for more details about how this works.

Example of defining an :class:`.Element` class
----------------------------------------------

Here is an example of defining a new element, with code comments explaining
the different parts::

    # Import any modules, classes or functions used in our code.
    from kqcircuits.elements.element import Element
    from kqcircuits.pya_resolver import pya
    from kqcircuits.util.parameters import Param, pdt
    from kqcircuits.util.symmetric_polygons import polygon_with_vsym


    # Any KQCircuits element must inherit from Element.
    class SimpleCross(Element):

        # Define PCell parameters for this class here.
        # Each parameter definition contains the parameter type, description and default value.
        # Other optional data such as the unit can also be defined for parameters.
        arm_length = Param(pdt.TypeDouble, "Cross arm length", 100, unit="μm")

        # The build() function is where the element geometry is built.
        def build(self):
            # We define a hardcoded value for arm_width, so it cannot be changed from outside like arm_length.
            arm_width = 30
            # Define some variables to hold values used commonly in this function.
            len1 = arm_width/2
            len2 = arm_width/2 + self.arm_length
            # Define the cross polygon using a list of DPoints.
            cross_poly = pya.DPolygon([
                pya.DPoint(-len1, -len2),
                pya.DPoint(-len1, -len1),
                pya.DPoint(-len2, -len1),
                pya.DPoint(-len2, len1),
                pya.DPoint(-len1, len1),
                pya.DPoint(-len1, len2),
                pya.DPoint(len1, len2),
                pya.DPoint(len1, len1),
                pya.DPoint(len2, len1),
                pya.DPoint(len2, -len1),
                pya.DPoint(len1, -len1),
                pya.DPoint(len1, -len2),
            ])
            # Add the cross polygon to the cell.
            # We use the get_layer() function to select in which layer the polygon is added.
            self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(cross_poly)

To include this element in the KQCircuits element library, copy this code to a
new Python-file ``simple_cross.py`` in the
``klayout_package/python/kqcircuits/elements`` folder. Then ``SimpleCross``
can be used like any other KQCircuits element.

Example of defining a Chip and inserting elements into it
---------------------------------------------------------

Many elements not only create their own geometry from scratch, but also
include other elements as subcells. This is especially true for chips, which
typically use existing elements as building blocks instead of producing shapes
directly. In this example we show how to place instances of the ``SimpleCross``
element created in the previous section into a new chip::

    from kqcircuits.chips.chip import Chip
    from kqcircuits.elements.simple_cross import SimpleCross
    from kqcircuits.pya_resolver import pya


    # New chip implementation must use the Chip element as a base class.
    # As chips are also elements, all the previous explanations about
    # parameters, build-method etc. hold also for them.
    class NewChip1(Chip):

        def build(self):

            # The produce_launchers function creates launchers fitting a certain
            # sampleholder and sets the chip size accordingly. The available
            # sampleholder types are defined in defaults.py (default_sampleholders).
            self.produce_launchers("SMA8")

            # Define variable for half chip width for positioning elements
            half_width = self.box.width()/2

            # Elements can be inserted to other elements (including chips) using the insert_cell function.
            # Giving the class name, instance transformation and pcell parameters, it creates a cell
            # object with the given parameter values and places an instance of that cell inside this cell
            # with the given transformation.
            # (Note that the chip origin is at the bottom left corner of the chip)
            self.insert_cell(SimpleCross, pya.DTrans(half_width, half_width), arm_length=200)

            # Another option is to first create the cell separately using add_element, and then insert
            # instances of that cell using insert_cell. This can be useful when placing many instances
            # with the same parameter values.
            cross_cell = self.add_element(SimpleCross, arm_length=150)
            self.insert_cell(cross_cell, pya.DTrans(half_width - 2000, half_width - 2000))
            self.insert_cell(cross_cell, pya.DTrans(half_width - 2000, half_width + 2000))
            self.insert_cell(cross_cell, pya.DTrans(half_width + 2000, half_width + 2000))
            self.insert_cell(cross_cell, pya.DTrans(half_width + 2000, half_width - 2000))

This code can be copied to a new Python-file ``new_chip1.py`` in the
``klayout_package/python/kqcircuits/chips`` folder to make it visible in the
KQCircuits chip library.

Defining sampleholder types
^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the previous example we used::

    self.produce_launchers("SMA8")

to make the chip have the correct launchers and size for fitting in an
"SMA8"-type sampleholder. The available sampleholder types are  defined in
:git_url:`defaults.py <klayout_package/python/kqcircuits/defaults.py>`
``default_sampleholders``. You can add new sampleholder types there, for
example::

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

A quick way to check all available sampleholder types is to use the
:class:`.Launchers` chip and change its ``sampleholder_type`` parameter.

Refpoints
---------

In an Element definition ``refpoints`` is just a dictionary of points. You can add to it by
assigning a point to a name, ``self.refpoints['name'] = pya.DPoint(...)``.

There are several ways the refpoints are used:

- The dictionary of a particular Element instance is returned by ``self.insert_cell()``. So you can
  insert a cell and then use the refpoints as references where to place other elements in relation
  to them.
- If you pass an ``inst_name`` argument to ``insert_cell()`` the refpoints are also named uniquely
  for the instance as ``{inst_name}_{refpoint_name}`` and added as text instances to the layout.
  This way you can later look up the points by name.
- ``insert_cell`` also has a ``rec_levels`` argument which determines now many layers down the
  hierarchy the refpoints are added.

As an example of using refpoints, let us extend the NewChip1 code from
previous section. Here we add a waveguide from a launcher to a capacitor
using refpoints::

    # In addition to the imports from previous example, import these:
    from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
    from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare


    class NewChip1(Chip):

        def build(self):

            # After produce_launchers call, there will be "chip-level" refpoints in self.refpoints.
            # These refpoints have prefixes corresponding to launcher names, such as "WN" for one
            # of the SMA8 launchers. Same is true for elements inserted with an inst_name.
            self.produce_launchers("SMA8")

            # ... other code here ...

            # insert_cell can return a dictionary of refpoints for the inserted element
            _, cap_refpoints = self.insert_cell(FingerCapacitorSquare, pya.DTrans(1, False, 5000, 3000))
            # Refpoints can be used to position WaveguideCoplanar path points or WaveguideComposite nodes.
            self.insert_cell(
                WaveguideCoplanar,
                path=pya.DPath([
                    # "Chip-level" refpoints with launcher name prefix "WN"
                    self.refpoints["WN_port"],
                    self.refpoints["WN_port_corner"],
                    # Refpoints of the capacitor element instance (no instance name prefix)
                    cap_refpoints["port_b_corner"],
                    cap_refpoints["port_b"],
                ], 0),
            )


How to use the points once they exist? Several styles have evolved:

- Just use them as a point and perhaps do some geometry calculations to come up with other points
  relative to it. This style is mostly useful inside element code, since it is there you really need
  to decide on geometry.
- On the Chip or Simulation level you can use ``align`` and ``align_to`` arguments of
  ``insert_cell()``. These can be either a point or a string name referring to a refpoint name, and
  will displace (but not rotate!) the element such that the two points overlap. For example,
  ``insert_cell(SomeElement, align="refpoint_of_some_element",
  align_to=self.refpoints["existing_ref"])``.

There is a convention followed almost everywhere: Places where you normally connect coplanar
waveguides have a refpoint named ``something_port`` and a second refpoint ``something_port_corner``
which is one corner-radius (``r``) away and indicates the direction that the connecting waveguide
should go. You can connect a waveguide correctly by routing it from ``something_port`` to
``something_port_corner``, and then wherever you want to go (can't do more than 90 degree turns this
way!). This point is also useful in simulations to pass to ``produce_waveguide_to_port()``.

The :class:`.WaveguideComposite` element has some logic where you can insert arbitrary elements
inside waveguides and it uses these points to align and connect them correctly.

Refpoints are not visible by default in KLayout. Enable the ``texts/refpoints`` layer to see all
refpoints. If there are many overlapping refpoints the texts can be hard to read. In this case, the
``texts/top refpoints`` layer may be used to see only the top-level refpoints. For this choose a new
top cell by right clicking the chip in the cell view of KLayout and selecting "Show As New Top".
This can be very useful to see "chip-level" refpoints only.

Faces
-----

KQCircuit layers are grouped by faces and functionality. A chip's "face" intuitively means the
bottom or top sides of it. To identify faces in multi chip configurations we number the chips from
"1". For technical reasons we permit multiple faces in a particular side. For example "2b1" denotes
the bottom face of the 2nd chip in a typical flip-chip configuration. See more details in
:git_url:`default_layer_config.py <klayout_package/python/kqcircuits/layer_config/default_layer_config.py>`.

Elements support a concept of **faces**, used for 3D-integrated chips to place shapes in layers
belonging to different sides of (possibly) different wafers. For example, an
element may create shapes in face 0 and face 1, and the ``face_ids`` parameter
of the element determines which actual chip faces ``0`` and ``1`` refer to.
By default, KQC elements have ``face_ids=["1t1","2b1","2t1"]``, so face 0 would be
"1t1" and face 1 would be "2b1".

To choose which face/layer a shape is placed in, you can use the ``face_id``
argument of ``self.get_layer``::

    # (the face_id passed to self.get_layer is actually an index to self.face_ids)
    self.cell.shapes(self.get_layer("indium_bump", face_id=0)).insert(pya.DBox(0, 500, 500, 0))
    self.cell.shapes(self.get_layer("indium_bump", face_id=1)).insert(pya.DBox(100, 400, 400, 100))

Note that by default ``face_id=0`` will be used in ``get_layer``, so it could
be omitted. It is also possible to change the face in which subcells are
placed in::

    # Placing a single-face element in a different face than the default
    self.insert_cell(Launcher, face_ids=[self.face_ids[1]])
    # Placing a multi-face element with the parts in different faces swapped
    self.insert_cell(FlipChipConnectorRf, face_ids=[self.face_ids[1], self.face_ids[0]])

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

KQCircuit's Layers
------------------

KLayout's right panel shows a layer tree. Layers containing meaningful device geometry are grouped
by faces: ``1t1-face``, ``2b1-face`` and ``2t1-face``. By default layer numbers 0-127 are used for
the bottom face of the chips and 128-255 are used for the top face, and the data type indicates the
chip number (data type 0 is used for layers not belonging to chip faces). Other texts, annotations
and miscellaneous things not strictly belonging to a particular face are under the ``texts`` layer
group. Other layers used only for simulations are under the aptly named ``simulations`` layer group.

Most layers have self-describing names like ``refpoints`` or ``instance names`` but others need a
bit of explanation:

- ``base metal gap`` -- Important layer with the final geometry of chips *in masks*. It has the
  shapes of gaps (areas without metal) in the base metal layer that is laid out on a silicon
  substrate.  Note that this layer is populated during mask export and therefore usually empty. It is hidden by default.

- ``base metal gap wo grid`` -- Like above, it has the gaps around shapes "etched" into metal but
  *without* the ground grid that is slow to produce.  This is the most used layer in elements.

- ``groud grid`` -- This layer is auto generated if the "Make ground plane grid" PCell parameter is
  enabled in a chip. It fills in the chip area *outside* of shapes in the ``ground grid avoidance``
  layer with a metal grid.  Technically, this layer contains the square shaped gaps in the grid, not
  the metal grid itself. Hidden by default.

- ``base metal addition`` -- Puts back metal to places where it is already removed. This is a
  technical layer helping us to construct the final shapes in a more elegant way, particularly here:
  ``base_metal_gap = base_metal_gap_wo_grid + ground_grid - base_metal_addition``. It is also used
  in ``base metal gap for EBL``, i.e. Electron Beam Litography.

Find more details in `defaults.py <../api/kqcircuits.defaults.html>`_.


Opening :class:`.Element` or :class:`.Chip` from an IDE
-------------------------------------------------------

You can use :git_url:`util/create_element_from_path.py` to open a
:class:`.Element` or :class:`.Chip` in KLayout from your IDE (or just straight from the
command-line).  The script is used as::

    klayout -e -rx -rm util/create_element_from_path.py -rd element_path=kqcircuits/chips/demo.py

And can be easily incorporated as a macro to your IDE.  Check the comments in the function on how to
use it in PyCharm or Visual Studio Code. The ``element_path`` argument can strip a leading
`*Circuits/klayout_package/python/` or `klayout_package/python/`, use what is easiest to implement
for your workflow.
