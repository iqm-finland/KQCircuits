.. _simulation_object:

Simulation objects
==================

The geometry of a simulation must be defined in a simulation object, which is an instance of a dedicated subclass of
either :class:`.Simulation` or :class:`.CrossSectionSimulation` classes.

The :class:`.Simulation` is the base class for typical 3-dimensional simulation geometries.
The :class:`.CrossSectionSimulation` is the base class for cross-sectional simulations, where the geometries are
typically 2-dimensional cross-sections of waveguides.
Both are intended to be subclassed by a specific simulation implementation.

This user guide mainly focuses on the usage of :class:`.Simulation` class.
See the section :ref:`Cross-sectional simulations` for more information on the cross-sectional simulations.

The Simulation class
^^^^^^^^^^^^^^^^^^^^

The :class:`.Simulation` class works very similar with typical KQCircuits elements: the subclass should implement a
:py:meth:`~kqcircuits.simulations.simulation.Simulation.build` method which generates the geometry and ports, typically
by inserting other elements into the model.
See also the :py:meth:`~kqcircuits.elements.element.Element.build` method of class :class:`.Element`.

Convenience class method :py:meth:`~kqcircuits.simulations.simulation.Simulation.from_cell` is provided to create a
simulation object from an existing cell.
In this case, the :class:`.Simulation` class doesn't have to be subclassed and no ports will be added.
See :ref:`Geometry from KLayout GUI` for more information.

Box
"""

The :class:`.Simulation` class introduces several PCell parameters to tune the simulation geometry.
One of them is ``box``, which defines the x- and y-dimensions of the simulation domain.
The value of ``box`` should be given as |pya.DBox|_.

.. hack to get monospaced URLs
.. |pya.DBox| replace:: ``pya.DBox``
.. _pya.DBox: https://www.klayout.de/doc-qt5/code/class_DBox.html

In practice, the parameter ``box`` can be used to limit the area that is taken into account in the simulation
and/or to define the margins around the relevant shapes.
One should consider carefully on a case-by-case basis what is suitable simulation area for the purpose.

.. image:: ../../images/gui_workflows/simulation_area.svg

Ports
"""""

Ports typically define the input source terms of the simulation and distinguish the signal and ground metals from each
other.
Two types of ports are supported, :class:`.InternalPort` between metal layers inside the geometry and
:class:`.EdgePort` at the edge of the simulation box.
Ports should be defined in the ``build`` method by adding instances of the port classes to the pre-defined list
``Simulations.ports``.

An internal port is created by supplying an integer representing the port number and two ``pya.DPoint`` points
``signal_location`` and ``ground_location`` for the :class:`.InternalPort` class builder.
The points should be located on opposite edges of two metal islands, and the actual port will be drawn as a polygon
between these edges (the opposing edges become two of the polygon edges).
For example, the following snippet adds an internal port across the junction of a single-island qubit, assuming that
``refp`` is the list of :class:`.Refpoints` obtained when inserting the corresponding qubit cell.::

    self.ports.append(
        InternalPort(number=1, signal_location=refp["port_squid_a"], ground_location=refp["port_squid_b"])
    )

An edge port is added similarly by creating an instance of :class:`.EdgePort`.
The mandatory parameters for :class:`.EdgePort` class builder are the port number and the ``signal_location``, which
must be located on the edge of ``Simulation.box``.

The convenience method :py:meth:`~kqcircuits.simulations.simulation.Simulation.produce_waveguide_to_port` draws a
waveguide from a specified location and in a specified direction, and adds the required port at the end of the
waveguide.
It supports both internal and edge ports, for example::

    # Create a 100um long waveguide that ends in an internal port
    self.produce_waveguide_to_port(location=refp["port_2"], towards=refp["port_2_corner"], port_nr=2,
                                   use_internal_ports=True, waveguide_length=100)

    # Create a waveguide that bends and terminates as an edge port on the right side of Simulation.box
    self.produce_waveguide_to_port(location=refp["port_3"], towards=refp["port_3_corner"], port_nr=3,
                                   use_internal_ports=False, side="right")

.. note::
    The ports are multipurpose and their implementation depends on the selected external simulation tool.
    For example in Ansys HFSS, the internal ports are mapped as a `Lumped Ports` and the edge ports are mapped as
    `Terminal Wave Ports`.
    In Q3D and Elmer capacitance simulations ports are used only to distinguish signal, ground, and floating islands
    and actual port polygons are omitted.
    For qubits with multiple islands, usually a separate port is needed for each island.

Face stack
""""""""""

The 3-dimensional geometry is built of uniform thickness dielectric substrates, which are typically separated from
each other by vacuum.
The thin metal and dielectric layers and other objects can be applied on any of the imaginable substrate surface and
between faces.
For example airbridges can be inserted to 3d geometry by drawing the shapes on ``airbridge pads`` and
``airbridge_flyover`` layers.
Also metal connections between chips or between two sides of a chip can be applied using ``indium bump`` or
``through silicon via`` layers, respectively.
The shapes of indium bumps and through silicon vias must be drawn on both the lower and upper faces of the joint.

The number of substrates is determined with two parameters, ``face_stack`` and ``lower_box_height``:

* The list ``face_stack`` determines which faces are taken into account in the simulation. The faces are listed from bottom to top and the length of ``face_stack`` describes how many surfaces are taken into account in the simulation.
* The parameter ``lower_box_height`` determines if the first term in ``face_stack`` corresponds to bottom or top surface of the lowest substrate. That is, if ``lower_box_height`` > 0, there will be a vacuum box below the lowest substrate, and the counting of faces will start from the bottom surface of the lowest substrate. Otherwise, the counting of faces will start from the top surface of the lowest substrate.

The following figure indicates the parameterization of the most typical 3-dimensional layouts.
The green and purple colors in the cross-sectional image illustrate substrate and thin metal layers, respectively.

.. image:: ../../images/gui_workflows/face_stack.svg

The single chip geometry (left figure) is used by default, and two-substrate flip-chip geometry (middle figure) is
typically obtained by setting::

    face_stack = ['1t1', '2b1']

To produce multiple layers on a substrate interface one can introduce ``face_stack`` as list of lists.
In that case, all the metal and dielectric layers of the inner list faces are piled up on the corresponding surface
in the respective order.
That means, the first term in the inner list indicates the face that is closest to the substrate.
One can use empty list in face_stack to leave certain surface without metallization.

Thicknesses of substrates (``substrate_height``) and vacuum boxes between chips (``chip_distance``) can be determined
individually from bottom to top or with single value.
Any of the heights can be left zero, to indicate that there is no vacuum between the chips or substrate between
the vacuum boxes.
Also, the metal thickness (``metal_height``) can be set to zero, but that means the metal layer is modelled as
infinitely thin sheet.
A dielectric layer is added on top of the metal layer if non-zero ``dielectric_height`` is given.


Simulation subclass
^^^^^^^^^^^^^^^^^^^

Subclassing the :class:`.Simulation` is similar to subclassing the :class:`.Element`, since both classes support most
of the same concepts.
For example, :ref:`python_workflow_refpoints` can be used to connect child elements together and
simulations can have :ref:`python_workflow_parameters` with the same syntax as in :class:`.Element`.
A simulation subclass can inherit parameters from regular elements with the :py:func:`.add_parameter` and
:py:func:`.add_parameters_from` decorators.

Single element subclass
"""""""""""""""""""""""

To save you the trouble of writing a :class:`.Simulation` subclass for single element simulations, you can use the
:py:meth:`~kqcircuits.simulations.single_element_simulation.get_single_element_sim_class` class builder method, provided
that the element class to be simulated has the :py:meth:`~kqcircuits.elements.element.Element.get_sim_ports` method
implemented.

For example, suppose we want to simulate a :class:`.Swissmon` qubit.
The simplest way to do it is to use the class builder to build a single element simulation::

    from kqcircuits.qubits.swissmon import Swissmon
    from kqcircuits.simulations.single_element_simulation import get_single_element_sim_class
    from kqcircuits.util.export_helper import get_active_or_new_layout

    sim_class = get_single_element_sim_class(Swissmon)  # Builds a simulation class for Swissmon

    layout = get_active_or_new_layout()
    sim_parameters = {}  # Dictionary of Swissmon parameters
    simulation = sim_class(layout, **sim_parameters)  # Builds an instance of the simulation class

Returned ``sim_class`` is a dynamically built subclass of :class:`.Simulation` that contains a cell of
the Swissmon qubit placed at the center of the simulation box.
``sim_class`` can be instantiated with a parameters dict that sets the parameter values to the internal Swissmon PCell.

You can see that currently
the :git_url:`Swissmon code <klayout_package/python/kqcircuits/qubits/swissmon.py>`
defines one :class:`.RefpointToSimPort` object to return in the
``get_sim_ports`` method. That is the :class:`.JunctionSimPort`,
which with default arguments places an internal port between refpoints ``"port_squid_a"`` and ``"port_squid_b"``.

Suppose we want to also have waveguides connected to the Swissmon couplers in the simulation. We can do this
by simply adapting the function :py:meth:`~kqcircuits.qubits.swissmon.Swissmon.get_sim_ports` to additionally return
:class:`.WaveguideToSimPort` objects that lead from refpoints on the Swissmon couplers ``"port_cplr0"``,
``"port_cplr1"`` and ``"port_cplr2"`` to refpoint specified by the ``towards`` keyword argument of
:class:`.WaveguideToSimPort`. That is::

    @classmethod
    def get_sim_ports(cls, simulation):
        return [JunctionSimPort(), WaveguideToSimPort('port_cplr0'),
                WaveguideToSimPort('port_cplr1'), WaveguideToSimPort('port_cplr2')]

If we then decide to not produce the waveguides for the next simulation, instead of reverting the change we just made
to :class:`.Swissmon` we can specify which refpoints should not generate ports in the simulation object::

    sim_class = get_single_element_sim_class(Swissmon, ignore_ports=['port_cplr0', 'port_cplr1', 'port_cplr2'])

For more information on how to use the :py:meth:`~kqcircuits.simulations.single_element_simulation.get_single_element_sim_class`
simulation class builder, please consult the API docs for the method
as well as the API docs for different implementations of the :class:`.RefpointToSimPort`.

General subclass
""""""""""""""""

Instead of using the class builder we can also create the simulation subclass manually. The following code snippet
implements essentially the same simulation class as was returned by the
:py:meth:`~kqcircuits.simulations.single_element_simulation.get_single_element_sim_class` class builder::

    from kqcircuits.pya_resolver import pya
    from kqcircuits.qubits.swissmon import Swissmon
    from kqcircuits.simulations.port import InternalPort
    from kqcircuits.simulations.simulation import Simulation
    from kqcircuits.util.export_helper import get_active_or_new_layout
    from kqcircuits.util.parameters import add_parameters_from


    @add_parameters_from(Swissmon, '*', junction_type="Sim", fluxline_type="none")
    class SwissmonSimulation(Simulation):
        def build(self):
            # Place a Swissmon qubit in the center of the simulation
            _, refpoints = self.insert_cell(Swissmon, trans=pya.DTrans(self.box.center()))

            # Add waveguide ports to the three couplers
            self.produce_waveguide_to_port(refpoints['port_cplr0'], refpoints['port_cplr0_corner'], 1, 'left')
            self.produce_waveguide_to_port(refpoints['port_cplr1'], refpoints['port_cplr1_corner'], 2, 'top')
            self.produce_waveguide_to_port(refpoints['port_cplr2'], refpoints['port_cplr2_corner'], 3, 'right')

            # Add junction port
            self.ports.append(InternalPort(4, refpoints['squid_port_squid_a'], refpoints['squid_port_squid_b']))

    layout = get_active_or_new_layout()
    sim_parameters = {}  # Dictionary of Swissmon parameters
    simulation = SwissmonSimulation(layout, **sim_parameters)  # Builds an instance of the simulation class

This could be a better approach if further flexibility is required, for example, to place multiple elements
into the same simulation or to simulate full chips or portions of the chip.

Geometry sweeps
^^^^^^^^^^^^^^^

Once a simulation subclass is defined, instance of it can be created with desired parameter values by passing keyword
arguments to the constructor.
An instance of a simulation subclass (also called a simulation object) represents single geometry variation.
The procedure to create and simulate multiple geometry variations is to create multiple simulation objects and store
them into a list.

There are helper functions :py:func:`.sweep_simulation` and :py:func:`.cross_sweep_simulation` to ease the construction
of geometry sweeps. The difference of these functions is that the :py:func:`.sweep_simulation` varies single parameter
at time as the :py:func:`.cross_sweep_simulation` cross-varies the parameters to go through all parameter combinations.

The following script shows how to generate some instances of the simulation subclass and create sweep over the
`gap_width` parameter::

    from kqcircuits.qubits.swissmon import Swissmon
    from kqcircuits.simulations.export.simulation_export import sweep_simulation
    from kqcircuits.simulations.single_element_simulation import get_single_element_sim_class
    from kqcircuits.util.export_helper import get_active_or_new_layout

    sim_class = get_single_element_sim_class(Swissmon)  # Builds a simulation class for Swissmon

    layout = get_active_or_new_layout()
    simulations = []

    # Generate the simulation with default parameters
    simulations.append(sim_class(layout))

    # Generate the simulation for some other parameter
    simulations.append(sim_class(layout, arm_length=[500, 500, 500, 500], name='arm_length_500'))

    # Make a 4-point sweep of gap width
    simulations += sweep_simulation(
        layout,
        sim_class,
        sim_parameters={
            'name': 'gap_sweep',
            'arm_length': [500, 500, 500, 500],
        },
        sweeps={
            'gap_width': [[x, x, x, x] for x in [10, 15, 20, 25]],
        }
    )
