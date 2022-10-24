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
        'n_workers': 2, # <--------- This defines the number of 
                        #            parallel independent processes.
                        #            Moreover, adding this line activates
                        #            the use of the simple workload manager.
    }

Additionally, Slurm is supported for cluster computing (also available for desktop computers with Linux/BSD operating systems).
For example, in the `waveguides_sim_compare.py` in case ``use_sbatch=True`` then the ``workflow['sbatch_parameters']`` is defined:

.. code-block::

    if use_sbatch:  # if simulation is run in a HPC system,
                    # sbatch_parameters can be given here
        workflow['sbatch_parameters'] = {
            '--job-name':sim_parameters['name'],
            '--account':'project_0',
            '--partition':'test',
            '--time':'00:10:00',
            '--ntasks':'40',
            '--cpus-per-task':'1',
            '--mem-per-cpu':'4000',
        }

And consequently, running `simulation.sh`, the tasks will be sent to Slurm workload manager.

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
