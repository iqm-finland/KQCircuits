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
The S-parameter feature is activated using parameter ``ansys_tool='hfss'``.
The relevant ``ansys_export`` parameters and their default values are listed below::

    export_parameters.update({
        'ansys_tool': 'hfss',  # Determines whether to use HFSS ('hfss'), Q3D Extractor ('q3d') or HFSS eigenmode ('eigenmode')
        'frequency_units': "GHz",  # Units of frequency.
        'frequency': 5,  # Frequency for mesh refinement. To set up multifrequency analysis in HFSS use list of numbers.
        'max_delta_s': 0.1,  # Stopping criterion in HFSS simulation.
        'percent_refinement': 30,  # Percentage of mesh refinement on each iteration.
        'maximum_passes': 12,  # Maximum number of iterations in simulation.
        'minimum_passes': 1,  # Minimum number of iterations in simulation.
        'minimum_converged_passes': 1,  # Determines how many iterations have to meet the stopping criterion to stop simulation.
        'sweep_enabled': True,  # Determines if HFSS frequency sweep is enabled.
        'sweep_start': 0,  # The lowest frequency in the sweep.
        'sweep_end': 10,  # The highest frequency in the sweep.
        'sweep_count': 101,  # Number of frequencies in the sweep.
        'sweep_type': 'interpolating',  # choices are "interpolating", "discrete" or "fast"
    })

The open-source alternative to calculate S-parameters is to use ``elmer_export`` with the export parameter
``tool='wave_equation'``.
For other relevant export parameters, please consult API docs for the function
:func:`~kqcircuits.simulations.export.elmer.elmer_export.export_elmer`.

Capacitance matrix
^^^^^^^^^^^^^^^^^^

The primary use case of a capacitance matrix simulation is to estimate capacitive couplings between different elements.
The output of a capacitance simulation is a mutual capacitance matrix between islands of signal metals.
In the mutual capacitance matrix, a non-diagonal term ``C_i_j`` is the capacitance between two signals ``i`` and ``j``,
and a diagonal term ``C_i_i`` is the capacitance between signal ``i`` and the ground.

The signal islands are determined by the ports of the simulation object and they are ordered by the port order number.
The port variable ``signal_location`` determines the location of the signal island.
The variable ``ground_location`` can be used to force any floating metal island as the ground.

From Ansys tool package, the Q3D solver is recommended for capacitance simulations.
This is activated with export parameter ``ansys_tool='q3d'``.
The other relevant parameters and their default values are::

    export_parameters.update({
        'ansys_tool': 'q3d',  # Determines whether to use HFSS ('hfss'), Q3D Extractor ('q3d') or HFSS eigenmode ('eigenmode')
        'percent_error': 0.1,  # Stopping criterion in Q3D simulation.
        'percent_refinement': 30,  # Percentage of mesh refinement on each iteration.
        'maximum_passes': 12,  # Maximum number of iterations in simulation.
        'minimum_passes': 1,  # Minimum number of iterations in simulation.
        'minimum_converged_passes': 1,  # Determines how many iterations have to meet the stopping criterion to stop simulation.
    })

The capacitance matrix simulations are also available with Ansys HFSS framework, which is useful in case if only HFSS
license is available.
For the usage one must perform a HFSS S-parameter simulation as indicated above and use the export parameter
``capacitance_export=True``.
This method assumes a purely capacitive model and is valid as long as the resulting ``C_i_j`` are constant over
frequency.

The Elmer export provides the open source alternative for capacitance matrix simulations.
The Elmer capacitance matrix simulation can be activated by using ``elmer_export`` with the export parameter
``tool='capacitance'``.
Please consult API docs of :func:`~kqcircuits.simulations.export.elmer.elmer_export.export_elmer` for more information.

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
``inductance`` parameters.

Ansys HFSS Eigenmode solution type is employed in the eigenmode simulations.
The eigenmode simulations are activated by using ``export_ansys`` with export parameter ``ansys_tool='eigenmode'``.
The other relevant parameters and their default values are::

    export_parameters.update({
        'ansys_tool': 'eigenmode',  # Determines whether to use HFSS ('hfss'), Q3D Extractor ('q3d') or HFSS eigenmode ('eigenmode')
        'frequency_units': "GHz",  # Units of frequency.
        'min_frequency': 5,  # the lower limit for eigenfrequency.
        'max_delta_f': 0.1,  # Maximum allowed relative difference in eigenfrequency (%).
        'n_modes': 2,  # Number of eigenmodes to solve.
        'percent_refinement': 30,  # Percentage of mesh refinement on each iteration.
        'maximum_passes': 12,  # Maximum number of iterations in simulation.
        'minimum_passes': 1,  # Minimum number of iterations in simulation.
        'minimum_converged_passes': 1,  # Determines how many iterations have to meet the stopping criterion to stop simulation.
    })

Energy integrals and participation ratio
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The energy integrals can be calculated from HFSS S-parameter or eigenmode simulations by setting export parameter
``integrate_energies=True`` in ``ansys_export`` function call.
The energy integrals of each simulation are stored into file ending with ``_energies.cvs``.
This file includes energy integrals of each surface/solid objects and the total energy integrated over all solid
material objects.

The energy participation ratios (EPRs) are calculated from energy integrals using the post processing script
``export_epr.py``.
This is activated by export parameter ``post_process_script='export_epr.py'``.
The EPRs are saved into a file ending with ``_epr.csv``.

.. _Cross-sectional simulations:

Cross-sectional simulations
^^^^^^^^^^^^^^^^^^^^^^^^^^^

KQCircuits offers possibility to export Elmer cross-sectional simulations to calculate capacitance and inductance per
unit length.
In cross-sectional simulations, the geometry is technically 2-dimensional, which enables more precise accuracy than
with the fully 3-dimensional simulations.
The reduced complexity of dimensions also allows a more detailed model to be used, for example considering the London
penetration depth of metals.
The cross-sectional simulations are valid only if the cross-section of the corresponding 3-dimensional geometry is
constant.
That includes for example waveguides.

The geometry of the cross-sectional simulations is described by an instance of a :class:`.CrossSectionSimulation`
subclass.
The cross-sectional simulation export follows similar logic to 3-dimensional simulations.
That is, you create a simulation subclass, create an empty folder for export files, build a list of simulation objects,
and call the :func:`~kqcircuits.simulations.export.elmer.elmer_export.export_elmer` function with suitable
``export_parameters``.
An example for simulating coplanar-waveguide cross-section can be found in
:git_url:`klayout_package/python/scripts/simulations/cpw_cross_section_sim.py`.

There is an additional ``Xsection`` tool to create cross-sectional geometries out of the x-y-layouts.
The tool is described in more details in :ref:`Creating cross section images` and an example simulation can be found in
:git_url:`klayout_package/python/scripts/simulations/waveguides_sim_xsection.py`.

.. _py-epr:

pyEPR
^^^^^

`pyEPR <https://github.com/zlatko-minev/pyEPR>`_ is supported for HFSS eigenmode simulations.
A pyEPR simulation is activated using ``ansys_tool='eigenmode'`` and ``simulation_flags=['pyepr']`` in the
``export_ansys`` function call.
An example simulation is found at :git_url:`klayout_package/python/scripts/simulations/xmons_direct_coupling_pyepr.py`.
See `pyEPR_example.ipynb <https://github.com/iqm-finland/KQCircuits-Examples/blob/main/notebooks/pyEPR_example.ipynb>`_
in the `KQCircuits-Examples <https://github.com/iqm-finland/KQCircuits-Examples/>`_ repository for an example on using
pyEPR itself.

The pyEPR can be used for TLS-limited :math:`T_1` estimation by using additional export parameter
``intermediate_processing_command='python "scripts/t1_estimate.py"'``.
This will run :git_url:`t1_estimate.py <klayout_package/python/scripts/simulations/ansys/t1_estimate.py>` between
queued simulations and compute the electrical participations in the lossy interfaces.
See :git_url:`double_pads_sim.py <klayout_package/python/scripts/simulations/double_pads_sim.py>` for an example and
`N. Savola, ‘Design and modelling of long-coherence qubits using energy participation ratios’, Master's thesis,
Aalto University, 2023`, for details on the method.
