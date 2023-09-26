.. _gmsh_elmer_export:

Gmsh/Elmer export
-----------------

Usage of Gmsh and Elmer export is similar to Ansys export.
The ``simulation`` object can be used with function ``export_elmer`` to export all necessary files to produce Gmsh/Elmer
simulations.

There is an example at :git_url:`klayout_package/python/scripts/simulations/waveguides_sim_compare.py`, which creates a simulation folder
with simulation scripts. The folder is created to `$TMP` (usually `kqcircuits/tmp`). The contents of the folder is something like::

    waveguides_sim_elmer
    ├── COMMIT_REFERENCE
    ├── scripts
    │   ├── elmer_helpers.py
    │   ├── gmsh_helpers.py
    │   └── run.py
    ├── sif
    │   ├── CapacitanceMatrix.sif
    │   └── electric_potential.pvsm
    ├── simulation.oas
    ├── simulation.sh
    ├── waveguides_n_guides_1.gds
    ├── waveguides_n_guides_1.json
    ├── waveguides_n_guides_1.sh
    ├── waveguides_n_guides_2.gds
    ├── waveguides_n_guides_2.json
    └── waveguides_n_guides_2.sh

`script` folder contains scripts that are used for preparing the simulations.

`sif` contains the Solver Input Files (SIF) for Elmer (scripts in `scripts` -folder are used
to build the SIF files for each simulation).

`waveguides_n_guides_1.sh`, `waveguides_n_guides_2.sh`, `...` are the shell scripts for running each simulation.
Each script executes Gmsh (mesh creation), computes the FEM model using Elmer (computes the
capacitance matrix), and visualizes the results using Paraview.

`simulation.sh` is a shell script for running all simulations at once.
The simulations are executed by running the `.sh` file in the output folder (here `waveguides_sim_elmer`).

Parallelization of the FEM computations has two levels: 
  1. independent processes, that are completely self consistent simulation processes that 
     do not need to communicate to other processes 
  2. dependent processes that are computing the same simulation and need to communicate
     with the others doing the same thing.

A workflow manager is needed for dealing with the first level and a multiprocessing paradigm for dealing
with the latter. Image below is a representation of these levels and their relationship:

.. raw:: html
    :file: ../../images/fem_parallelization_schemes.svg

By default, the simulations are run sequentially, but simple first-level parallelization can be enabled with ``n_workers`` in the `workflow` settings of :py:func:`.export_elmer`.
For example in `waveguides_sim_compare.py` defining the following will use two parallel workers for independent computations:

.. code-block::

    workflow = {
        'run_elmergrid': True,
        'run_elmer': True,
        'run_paraview': True,  # this is visual view of the results 
                               # which can be removed to speed up the process
        'python_executable': 'python', # use 'kqclib' when using singularity 
                                       # image (you can also put a full path)
        'elmer_n_processes': elmer_n_processes,  # <------ This defines the number of 
                                                 #         processes in the second level 
                                                 #         of parallelization. -1 uses all
                                                 #         the physical cores (based on 
                                                 #         the machine which was used to 
                                                 #         prepare the simulation)
        'elmer_n_threads': elmer_n_threads,  # <------ This defines the number of omp threads per process
        'n_workers': 2, # <--------- This defines the number of 
                        #            parallel independent processes.
                        #            Moreover, adding this line activates
                        #            the use of the simple workload manager.
    }

Note that Elmer has `elmer_n_processes` and `elmer_n_threads`. The first is number of MPI processes and the second
is number of OMP threads per process. It is usually most efficient to prefer MPI processes than threads.
However, when the mesh is small, it may be beneficial to increase the use of threads.

Additionally, Slurm is supported for cluster computing (also available for desktop computers with Linux/BSD operating systems). Slurm can be used by
defining ``workflow['sbatch_parameters']`` in the export script. An example can be found in ``waveguides_sim_compare.py``

When using Slurm the simulation is run in 2 parts as Gmsh benefits from using multiple threads while Elmer benefits from using multiple processes.

1. "Gmsh" part, also contains ElmerGrid calls and writing Elmer sifs. Only multithreading with single task and node
2. "Elmer" part. Runs ElmerSolver with any requested resources. Also runs writing the results and project version with single thread

Instead of forwarding the settings directly to ``sbatch`` command from ``workflow[sbatch_parameters]``, the following custom options are used:

.. code-block::

    workflow['sbatch_parameters'] = {
        'elmer_n_nodes': '1'        # Number of computing nodes
        'elmer_n_processes': '10'   # Total number of task (separate processes)
        'elmer_n_threads': '1'      # Number of threads per task                  
        'elmer_mem': '64G'          # Memory allocated for running Elmer
        'elmer_time': '00:10:00'    # Timeout for the elmer batch job

        'gmsh_n_threads':           # Number of threads used for gmsh
                                    # Note that this cannot exceed the available number
                                    # of threads per node on the used partition
        'gmsh_mem': '64G'           # Memory allocated for running gmsh          
        'gmsh_time': '00:10:00'     # Timeout for the gmsh batch job                    
    }

Additionally the account and partition info must be given:

.. code-block:: 

    workflow['sbatch_parameters'] = {
        '--account':   'project_0'
        '--partition': 'partition'
    }

All other keys in ``workflow['sbatch_parameters']`` starting with ``--`` are used directly in both parts of the simulation. 
However, note that the custom parameters might overwrite these. Keys without ``--``, which are none of the above are ignored.

By running ``RES=$(sbatch ./simulation_meshes.sh) && sbatch -d afterok:${RES##* } ./simulation.sh``, the tasks will be sent to 
Slurm workload manager such that the Elmer part will only start once processign the meshes is finished. 
For running the simulations on a remote machine see :ref:`elmer_remote_workflow`.


We recommend using the `n_workers` approach for simple systems when computing queues are not needed (no shared resources),
and Slurm approach for more complicated resource allocations (for example multiple users using the same machine).

Gmsh can also be parallelized (second level of parallelization) using OpenMP:

.. code-block::

    mesh_parameters = {
        'default_mesh_size': 100.,
        'gap_min_mesh_size': 2.,
        'gap_min_dist': 4.,
        'gap_max_dist': 200.,
        'port_min_mesh_size': 1.,
        'port_min_dist': 4.,
        'port_max_dist': 200.,
        'algorithm': 5,
        'gmsh_n_threads': -1,  # <---------- This defines the number of processes in the
                               #             second level of parallelization
                               #             -1 uses all the physical cores (based on the machine 
                               #             which was used to prepare the simulation)
        'show': True,  # For GMSH: if true, the mesh is shown after it is done
                       # (for large meshes this can take a long time)
    }

Please note that running the example requires the installation of

* Gmsh python API
  ``pip install gmsh``
* Elmerfem solver,
  see https://github.com/ElmerCSC/elmerfem
* Paraview
  https://www.paraview.org/

Gmsh API suffices if one needs to only generate the mesh.

.. note::

        If one does not want to install all the software to their computer (for example Gmsh or Elmer), 
        there is a possibility to use the `singularity` image. See :ref:`singularity_image`.
