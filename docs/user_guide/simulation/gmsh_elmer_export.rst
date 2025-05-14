.. _gmsh_elmer_export:

Gmsh/Elmer export
-----------------

Usage of Gmsh and Elmer export is similar to Ansys export.
The ``simulation`` object can be used with function ``export_elmer`` to export all necessary files to produce Gmsh/Elmer
simulations.

Prerequisites
*************

Setting up your system to successfully run simulations in Gmsh/Elmer requires following installations:

* Gmsh python API - ``pip install gmsh`` or in secure mode ``pip install -r path/to/sim-requirements.txt``
* Elmerfem solver,
  see https://github.com/ElmerCSC/elmerfem or https://www.elmerfem.org/blog/binaries/
* Paraview
  https://www.paraview.org/

Gmsh API suffices if one needs to only generate the mesh.

.. note::

        For linux systems (including Windows Subsystem for Linux - WSL), instead of installing Elmer yourself,
        you can pull a pre-installed `singularity` image we release periodically on GitHub.
        See :ref:`singularity_image`.

Exported simulation structure
*****************************

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

Parallelization
***************

Parallelization of the FEM computations has three levels:
  1. independent processes, that are completely self consistent simulation processes that
     do not need to communicate to other processes. This level of parallelism can be used with parameter sweeps
     where multiple Elmer simulations are needed. If the varied parameter does not affect meshing i.e. frequency
     or material parameters, the meshes will be only generated once for all simulations in the sweep.
     Number of parallel processes on this level can be controlled by setting ``n_workers`` in ``workflow``.
  2. dependent processes that are computing the same simulation and need to communicate
     with the others doing the same thing. This level of parallelism is handled by MPI.
     Number of dependent processes per independent process or simulation can be controlled
     by setting ``elmer_n_processes`` in ``workflow``.
  3. thread-level parallelism where multiple threads or cores are used per each dependent process.
     This is implemented using OpenMP. The number of threads per process can be controlled by
     setting ``elmer_n_threads`` in ``workflow``. It is usually also most efficient to prefer MPI processes than threads.
     However, when the mesh is small, it may be beneficial to increase the use of threads.

Image below is a representation of these levels and their relationship:

.. raw:: html
    :file: ../../images/fem_parallelization_schemes.svg

The total number of threads running in parallel will then be ``n_workers*elmer_n_processes*elmer_n_threads`` .
Requesting more computing resources than available might lead to poor performance.

If the parallelization settings are not explicitly stated in ``workflow``, the simulations are run sequentially. If the any
of the numbers are set to ``-1``, then as many processes/threads are used as available on the machine. For example in
`waveguides_sim_compare.py` defining the following will use two parallel workers for independent computation, with the number of
dependent processes automatically chosen. If there are 10 threads available on the computer then ``elmer_n_processes`` will be set
automatically to ``floor( 10 / n_workers)`` = 5.

.. code-block::

    workflow = {
        'run_gmsh_gui': True,    # <-------- For GMSH: if true, the mesh is shown after it is done, for large
                                 #           meshes this can take a long time
        'run_elmergrid': True,   # <-------- Run ElmerGrid to process the meshes to Elmer supported format
        'run_elmer': True,       # <-------- Run Elmer
        'run_paraview': True,    # <-------- Open visual view of the results. Can be set to False to speed up the process
        'python_executable': 'python', # <-- Can be used to choose alternative python executable. For example this could
                                       #     point to the singularity image via the symbolic link ``kqclib`` or full path
        'n_workers': 2, # <----------------- This defines the number of parallel independent processes. Can be used
                        #                    To parallelize different simulations in a parameter sweep.
                        #                    Setting this larger than 1 activates the use of the simple workload manager.
        'elmer_n_processes': -1,   # <------ This defines the number of
                                   #         processes in the second level
                                   #         of parallelization. -1 uses all
                                   #         the physical cores (based on
                                   #         the machine which was used to
                                   #         prepare the simulation)
        'elmer_n_threads': 1,  # <---------- This defines the number of omp threads per process
        'gmsh_n_threads': -1,  # <---------- This defines the number of processes in the
                               #             second level of parallelization. -1 uses all
                               #             the physical cores (based on the machine which
                               #             was used to prepare the simulation).
    }

Additionally, Slurm is supported for cluster computing (also available for desktop computers with Linux/BSD operating systems). Slurm can be used by
defining ``workflow['sbatch_parameters']`` in the export script. An example can be found in ``waveguides_sim_compare.py``

When using Slurm the simulation is run in 2 parts as Gmsh benefits from using multiple threads while Elmer benefits from using multiple processes.

1. "Gmsh" part, also contains ElmerGrid calls and writing Elmer sifs. Only multithreading with single task and node
2. "Elmer" part. Runs ElmerSolver with any requested resources. Also runs writing the results and project version with single thread

Instead of forwarding the settings directly to ``sbatch`` command from ``workflow[sbatch_parameters]``, the following custom options are used:

.. code-block::

    workflow['sbatch_parameters'] = {
        'n_workers': 2,             # <-- Number of parallel simulations, the total amount of resources requested
                                    #     is `n_workers` times the definitions below for single simulation
        'max_threads_per_node': 20, # <-- Max number of tasks allowed on a node. dependent on the used remote host
                                    #     Automatically divides the tasks to as few nodes as possible
        'elmer_n_processes':10,     # <-- Number of tasks per simulation
        'elmer_n_threads':1,        # <-- Number of threads per task
        'elmer_mem':'64G',          # <-- Amount of memory per simulation
        'elmer_time':'00:10:00',    # <-- Maximum time per simulation

        'gmsh_n_threads':10,        # <-- Threads per simulation
        'gmsh_mem':'64G',           # <-- Allocated memory per simulation
        'gmsh_time':'00:10:00',     # <-- Maximum time per simulation

        'env_setup_cmds': ["module load elmer"] # <- Optional commands which can be used to setup the environment on the remote platform.
                                                     An alternative is to add the commands to the remote profile file (e.g. `~/.bashrc`)
    }

Additionally the account and partition info must be given:

.. code-block::

    workflow['sbatch_parameters'] = {
        '--account':'project_0',    # <-- Remote account for billing
        '--partition':'test',       # <-- Slurm partition used, options depend on the remote
    }

The account can alternatively be set with an environment variable ``KQC_REMOTE_ACCOUNT``. All other keys in
``workflow['sbatch_parameters']`` starting with ``--`` are used directly in both parts of the simulation.
However, note that the custom parameters might overwrite these. Keys without ``--``, which are none of the above are ignored.

By running ``RES=$(sbatch ./simulation_meshes.sh) && sbatch -d afterok:${RES##* } ./simulation.sh``, the tasks will be sent to
Slurm workload manager such that the Elmer part will only start once processing the meshes is finished.
For running the simulations on a remote machine see :ref:`elmer_remote_workflow`.


We recommend using the `n_workers` approach for simple systems when computing queues are not needed (no shared resources),
and Slurm approach for more complicated resource allocations (for example multiple users using the same machine).

Gmsh can also be parallelized using OpenMP:

.. code-block::

    workflow = {
        'gmsh_n_threads': -1,  # <---------- This defines the number of processes in the
                               #             second level of parallelization
                               #             -1 uses all the physical cores (based on the machine
                               #             which was used to prepare the simulation)
    }
