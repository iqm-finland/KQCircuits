Creating a simulation object
============================

To export a simulation, the geometry to simulate must be defined in a simulation object, which is an instance of the
:class:`.Simulation` class. The :class:`.Simulation` class works very similar to regular KQCircuits elements: the
simulation should implement a :py:meth:`~kqcircuits.simulations.simulation.Simulation.build` method which generates the
geometry, typically by inserting other elements. See also the :py:meth:`~kqcircuits.elements.element.Element.build`
method of class :class:`.Element`.

.. note::
    Often, a simulation is defined in code by implementing a subclass of :class:`.Simulation`. This allows arbitrary
    geometry and port definitions. However, there are also macros and convenience methods to create simulations directly
    from existing geometry. See Geometry from KLayout GUI below for more information on these.

The :class:`.Simulation` class supports most of the same concepts as :class:`.Element`.
For example, :ref:`python_workflow_refpoints` can be used to connect child elements together and
simulations can have :ref:`python_workflow_parameters` with the same syntax as in :class:`.Element`. A simulation can
inherit parameters from regular elements with the :py:func:`.add_parameter` and :py:func:`.add_parameters_from`
decorators.

The parameter values can be set when creating an instance of the simulation, by passing keyword arguments to the
constructor. Parameters are often used to export parameter sweeps of a simulation, and there are helper functions
:py:func:`.sweep_simulation` and :py:func:`.cross_sweep_simulation` to generate sweeps. See :ref:`simulation_scripts`
for examples on their usage.

Simulation box
^^^^^^^^^^^^^^

The :class:`.Simulation` also has some extra features that are important for creating simulations. Fist of all,
the simulation area is defined by the ``box`` parameter, which should be a |pya.DBox|_.

.. hack to get monospaced URLs
.. |pya.DBox| replace:: ``pya.DBox``
.. _pya.DBox: https://www.klayout.de/doc-qt5/code/class_DBox.html

The simulation area should not be overly large; consider what is necessary for the purpose. Since ``box`` is a
parameter, it can be set during export.

.. image:: ../../images/gui_workflows/simulation_area.svg

Ports
^^^^^

Ports define the inputs and outputs of the simulation. Two types of ports are supported, :class:`.EdgePort` at the edge
of the simulation box and and :class:`.InternalPort` for ports inside the geometry. Ports are defined in the ``build``
method by adding instances of the corresponding port class to the pre-defined ``Simulations.ports`` list.

To create an internal port, two points ``signal_location`` and ``ground_location`` must be supplied as ``pya.DPoint``.
These must be exactly on the midpoint of geometry edges in the simulation. The actual port will be drawn as a rectangle
touching these edges. For example, the following snippet creates an internal port across the junction of a single-island qubit,
where ``refp`` is a :class:`.Refpoints` instance obtained when inserting the corresponding qubit cell.::

    self.ports.append(
        InternalPort(number=1, signal_location=refp["port_squid_a"], ground_location=refp["port_squid_b"])
    )

The :class:`.InternalPort` is mapped to a `Lumped Port` in Ansys HFSS. In Q3D and Elmer capacitance simulations only
``signal_location`` is used and ``ground_location`` can be omitted. For qubits with multiple islands, usually a
separate port is needed for each island.

Edge ports can be created similarly by adding :class:`.EdgePort` instances. Edge ports only
have a ``signal_location``, and it must be on the edge of ``Simulation.box``.

For ports that connect via waveguides, the convenience method
:py:meth:`~kqcircuits.simulations.simulation.Simulation.produce_waveguide_to_port` draws both the waveguide and adds
the required port. It supports both internal and edge ports, for example::

    # Create a 100um long waveguide that ends in an internal port
    self.produce_waveguide_to_port(location=refp["port_2"], towards=refp["port_2_corner"], port_nr=2,
                                   use_internal_ports=True, waveguide_length=100)

    # Create a waveguide that bends and terminates as an edge port on the right side of Simulation.box
    self.produce_waveguide_to_port(location=refp["port_3"], towards=refp["port_3_corner"], port_nr=3,
                                   use_internal_ports=False, side="right")

Example simulation
^^^^^^^^^^^^^^^^^^
In the following example, a Swissmon qubit is placed at the center of the simulation box, waveguide ports are connected
to the couplers, and an internal port is placed at the junctions::

    from kqcircuits.pya_resolver import pya
    from kqcircuits.qubits.swissmon import Swissmon
    from kqcircuits.simulations.port import InternalPort
    from kqcircuits.simulations.simulation import Simulation
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
            self.ports.append(InternalPort(3, refpoints['squid_port_squid_a'], refpoints['squid_port_squid_b']))

.. _simulation_scripts:

Simulation scripts
^^^^^^^^^^^^^^^^^^
Once a simulation class is defined, instances of it can be created with desired parameter values, and the instances
can be exported as geometry or to one of the supported simulation tools. The following example script shows how to
generate some instances and sweep a parameter, and export the resulting geometry as an OAS file.::

    from kqcircuits.klayout_view import KLayoutView
    from kqcircuits.simulations.export.simulation_export import export_simulation_oas, sweep_simulation
    from kqcircuits.util.export_helper import create_or_empty_tmp_directory

    view = KLayoutView()

    simulations = []

    # Generate the simulation with default parameters
    simulations.append(SwissmonSimulation(view.layout))

    # Generate the simulation for some other parameter
    simulations.append(SwissmonSimulation(view.layout, arm_length=[500, 500, 500, 500], name='arm_length_500'))

    # Make a 4-point sweep of gap width
    simulations.extend(sweep_simulation(
        view.layout,
        SwissmonSimulation,
        sim_parameters={
            'name': 'gap_sweep',
            'arm_length': [500, 500, 500, 500],
        },
        sweeps={
            'gap_width': [[x, x, x, x] for x in [10, 15, 20, 25]],
        }
    ))

    # Export the list of simulation instances as OAS file in the kqcircuits/tmp/swissmon_simulation_output folder
    dir_path = create_or_empty_tmp_directory("swissmon_simulation_output")
    export_simulation_oas(simulations, dir_path)

This script can be run as a regular python script, or in the KLayout macro editor. To run the example, place the
``SwissmonSimulation`` class definition above in the same file. The output files will be written to a folder in the
KQCircuits ``tmp`` folder.

The example above only exports an OAS file with the geometry. See the following sections for information on exporting
to different simulation tools.

More example scripts are available in :git_url:`scripts/simulations`.

Geometry from Klayout GUI
^^^^^^^^^^^^^^^^^^^^^^^^^

An alternative way to export simulations is by drawing the geometry (placing elements or drawing manually) in
KLayout, and running one of the following macros.

* :git_url:`scripts/macros/export/export_ansys.lym <klayout_package/python/scripts/macros/export/export_ansys.lym>`
* :git_url:`scripts/macros/export/export_sonnet.lym <klayout_package/python/scripts/macros/export/export_sonnet.lym>`

Similarly, simulation instances can be created from an existing KLayout Cell ``cell`` in code::

    simulation = Simulation.from_cell(cell, name='Dev', margin=100)

These methods export the geometry, but do not add any ports to the simulation. Hence, this is most useful if you want
to manually create ports or make other changes for example in Ansys.
