Simulation features
===================

The simulation export covers following types of simulations.

S-parameter matrix
^^^^^^^^^^^^^^^^^^

The output of a S-parameter (scattering parameter) simulation is a matrix of S-parameters between the ports.
The dimensions of the matrix is equal to number of ports given in the simulation object.
The rows and columns of the matrix are ordered by the port order number, i.e., the ``number`` parameter of
the class :class:`.Port`.

.. note::
    Some port variables like the ``renormalization`` of :class:`.Port` and the ``deembed_len`` of
    :class:`.EdgePort` take effect in the output S-parameter matrix. You can always double-check the value of any
    parameter from the exported json file.

The resulting S-parameter matrices are stored in ``SnP`` (Touchstone) file format, where the file
extension are ``.s1p``, ``.s2p``, ``.s3p``, and so forth).

In Ansys Electronic Desktop, the S-parameter simulation feature employs HFSS Terminal solution type.
The S-parameter feature is activated using the :class:`.AnsysHfssSolution` solution type or argument
``ansys_tool='hfss'`` in the :func:`~kqcircuits.simulations.export.ansys.ansys_export.export_ansys` function.

The open-source alternative to calculate S-parameters is to use
:func:`~kqcircuits.simulations.export.elmer.elmer_export.export_elmer` function with the
:class:`.ElmerVectorHelmholtzSolution` solution type or argument ``tool='wave_equation'``.
The Elmer S-parameter calculation is only partly supported at the moment.

Capacitance matrix
^^^^^^^^^^^^^^^^^^

The primary use case of a capacitance matrix simulation is to estimate capacitive couplings between different elements.
The output of a capacitance simulation is a mutual capacitance matrix between islands of signal metals.
In the mutual capacitance matrix, a non-diagonal term ``C_i_j`` is the capacitance between two signals ``i`` and ``j``,
and a diagonal term ``C_i_i`` is the capacitance between signal ``i`` and the ground.

The signal islands are determined by the ports of the simulation object and they are ordered by the port order number.
The port variable ``signal_location`` determines the location of the signal island. The variable ``ground_location``
can be used to force any floating metal island as the ground.

From Ansys tool package, the Q3D solver is recommended for capacitance simulations.
This is activated with the export parameter ``ansys_tool='q3d'`` or with solution type :class:`.AnsysQ3dSolution`.

The capacitance matrix simulations are also available with Ansys HFSS framework, which is useful in case if only HFSS
license is available.
For the usage one must perform a HFSS S-parameter simulation as indicated above and use the export parameter
``capacitance_export=True``.
This method assumes a purely capacitive model and is valid as long as the resulting ``C_i_j`` are constant over
frequency.

The Elmer export provides the open source alternative for capacitance matrix simulations.
The Elmer capacitance matrix simulation can be activated with the export parameter
``tool='capacitance'`` or with solution type :class:`.ElmerCapacitanceSolution`.

Eigenmode
^^^^^^^^^

An eigenmode simulation provides results in terms of eigenmodes, i.e. resonances of a given structure.
The output of an eigenmode simulation is a list of complex-valued eigenfrequencies, which
can be used to estimate resonance frequencies and/or lifetimes of the resonances.
The eigenfrequencies are given in the Ansys eigenmode data file format with file extension ``.eig``.

The solution method in eigenmode simulation is based on solving an
`eigenvalue problem <https://en.wikipedia.org/wiki/Eigenvalues_and_eigenvectors>`_.
Thus, the eigenmode simulations do not accept manually set source terms, and ports are not needed to define excitation.
Instead internal ports of a simulation object can be employed to generate lumped RLC boundary conditions into the model.
This is done by setting the port parameter ``junction=True`` and by giving the desired values in ``capacitance`` and
``inductance`` parameters. An internal port can be made floating by giving the parameter `floating=True`
(default `False`). This avoids the "ground side island" of the port becoming part of ground layer. This is recommended
in junctions between floating island qubit simulations.

Ansys HFSS Eigenmode solution type is employed in the eigenmode simulations.
The eigenmode simulations are activated by using :func:`~kqcircuits.simulations.export.ansys.ansys_export.export_ansys`
with argument ``ansys_tool='eigenmode'`` or with solution type :class:`.AnsysEigenmodeSolution`.

Energy integrals and participation ratio
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The energy integrals can be calculated from HFSS S-parameter or eigenmode simulations by setting solution argument
``integrate_energies=True``.
The energy integrals are computed for each surface/solid objects and the total energy is integrated over all solid
material objects.

The open-source alternative for computing energy integrals is activated by calling export function
:func:`~kqcircuits.simulations.export.elmer.elmer_export.export_elmer` with solution type :class:`.ElmerEPR3DSolution`
or argument ``tool='epr_3d'``. This simulation tool computes the capacitance matrix and the energy integrals for
each layer.

The energy participation ratios (EPRs) are calculated from energy integrals using the post processing script
``export_epr.py``.
This is activated by export parameter ``post_process_script='export_epr.py'``.
The EPRs are saved into a file ending with ``_epr.csv``.

.. _Cross-sectional simulations:

Cross-section simulations
^^^^^^^^^^^^^^^^^^^^^^^^^

KQCircuits offers possibility to export Ansys or Elmer cross-section simulations for modeling 3-dimensional objects,
such as waveguides, where the transverse geometry remain constant over a relatively long distance.
The geometry of cross-section simulation is technically 2-dimensional, which enables more precise accuracy than
available with the fully 3-dimensional simulations.
The reduced complexity of dimensions also allows a more detailed model to be used, for example considering the London
penetration depth of metals.
The cross-sectional simulations can be used to compute capacitance and inductance values per unit length and energy
integrals over layers.

The cross-section geometry is described in a subclass of :class:`.CrossSectionSimulation` by implementing the
:py:meth:`~kqcircuits.simulations.cross_section_simulation.CrossSectionSimulation.build` method.
Exporting a cross-section simulation follows similar logic to 3-dimensional simulation export.
That is, we create a simulation subclass, create an empty folder for export files, build a list of simulation objects,
and call the :func:`~kqcircuits.simulations.export.ansys.ansys_export.export_ansys` or
:func:`~kqcircuits.simulations.export.elmer.elmer_export.export_elmer` function with suitable parameters.
The available solution types for cross-section simulations are
:class:`.AnsysCrossSectionSolution` and :class:`.ElmerCrossSectionSolution`.
An example for building and exporting a cross-section simulation can be found in
:git_url:`klayout_package/python/scripts/simulations/cpw_cross_section_sim.py`.

It is possible to generate vertical cross section from 3-dimensional layer stack-up using the :class:`.CutSimulation`
class which is a subclass of the :class:`.CrossSectionSimulation`.
For this we create the 3-dimensional geometry as a :class:`.Simulation` object and then specify a line segment with
two points from which the cross section is formed.

Alternatively, we can produce multiple cross sections from a list of :class:`.Simulation` objects at once with the
:func:`~kqcircuits.simulations.export.cross_section.cross_section_export.create_cross_sections_from_simulations`
function. See
:git_url:`klayout_package/python/scripts/simulations/waveguides_sim_cross_section.py` for an example use case.

Cross sections are an essential part in calculating energy participation ratios for elements. See docstring in
:func:`~kqcircuits.simulations.export.cross_section.epr_correction_export.get_epr_correction_simulations`
and :git_url:`klayout_package/python/scripts/simulations/swissmon_epr_sim.py` for an example use case.
