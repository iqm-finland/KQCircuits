.. _docker_image:

Containers
==========

A Docker image for CLI and CI usage is included in :git_url:`ci/Dockerfile`.

The image can be built manually from the root of the repository with `-f ci/Dockerfile`.
Additionally, the KLayout version can be specified with ``--build-arg`` options by
providing the name of the KLayout package as ``KL_FILE`` and its MD5 hash as ``KL_HASH``::

  docker build -t kqcircuits -f ci/Dockerfile --build-arg KL_FILE=klayout_0.27.12-1_amd64.deb --build-arg KL_HASH=f5fbb6b33f96008bc7037c43b0bd6f24 .

See possible versions and hashes for Ubuntu 20 in the `KLayout website <https://www.klayout.de/build.html>`_.


CLI usage
---------

The image can be used to quickly generate files, such as masks and chips from Python scripts.
For example, to run a script ``m00x.py`` from a local directory, do the following::

   docker run --volume ${PWD}:/kqc/tmp ghcr.io/iqm-finland/kqcircuits:main tmp/m00x.py

This runs the script in a Docker container and on-default writes the output to ``/kqc/tmp``,
which is mounted to the working directory with ``--volume``.
More specifically, it executes the following command in :git_url:`ci/run_script.sh`::

   klayout -e -z -nc -rx -r tmp/m00x.py


Additional arguments can of course be given, such as variables through ``-wd <name>=<value>``.
See `CLI arguments for KLayout <https://www.klayout.de/command_args.html>`_ for more info.

.. note::
    If the script imports code like elements not included in KQCircuits,
    your local KQCircuits environment should be mounted to overwrite the one in the container.
    To this end, simply mount ``/kqc``.

If using the older HyperV backend on Windows, you might need to increase your RAM limit from the 1GB default depending on your usage. 
See `Docker Runtime options with Memory <https://docs.docker.com/config/containers/resource_constraints/#limit-a-containers-access-to-memory>`_ for details.

To override :git_url:`ci/run_script.sh` entirely, you can use the `Docker entrypoint argument <https://docs.docker.com/engine/reference/run/#entrypoint-default-command-to-execute-at-runtime>`_.

.. _docker_ci_usage:

Docker CI usage
---------------

The image is built and published automatically in the release workflow on version tags and pushes to the main branch.
It is then used to run all the tests in the CI pipeline.

Pull requests build the image but do not push it to the registry so that the changes may be tested to see
whether they break the image.


.. _singularity_image:

Singularity usage
-----------------

Singularity images are like docker images (https://sylabs.io/guides/3.0/user-guide/quick_start.html) that work better 
in HPC environments (https://singularity-tutorial.github.io/).
The latest image can be downloaded from the GitHub Container registry. It should be downloaded to a `libexec` folder
under :git_url:`singularity` with the name `kqclib`. This is performed as follows at the root of the repo::

   singularity pull singularity/libexec/kqclib oras://ghcr.io/iqm-finland/kqcircuits:main-singularity

The image can also be built manually in the :git_url:`singularity` folder by running::

   ./singularity.sh

After pulling or building, you can now run (again, in the :git_url:`singularity` folder)::

   ./create_links.sh

in order to get the executables for using the software in the image (instead of in your own system).

Among other executables, the image contains the following executables that are needed for the simulation workflow::

   EXECUTABLES=("ElmerSolver" "ElmerSolver_mpi" "ElmerGrid" "klayout" "kqclib" "paraview" "python")

You could add your own executable in the list in `create_links.sh` (it is just a symbolic link 
named like the executable that then needs to be found in the image).
Remember to add `path-to-your-KQCircuits/singularity/bin` to your `$PATH` environment variable.

You can now prepare KQC simulations using the image:
For example go to `path-to-your-KQCircuits/klayout_package/python/scripts/simulations/`
And run::

   kqclib waveguides_sim_compare.py

or::

   path-to-your-KQCircuits/python waveguides_sim_compare.py (make sure python is run from $PWD)

.. note::
   python is not put in $PWD/bin such that it does not over-ride the system python even if the 
   folder is added to PATH environment variable"

.. note::
   In `waveguides_sim_compare.py`, one has to set ``workflow['python_executable']='kqclib'`` or 
   ``workflow['python_executable']='path-to-your-KQCircuits/singularity/python'`` (in order to use
   the singularity image or override the system python with the latter executable, by moving it
   to path-to-your-KQCircuits/singularity/bin). 

.. warning::
   The singularity container can be used with Windows Subsystem for Linux (WSL) but problems with simulations
   getting stuck have been encountered while using the simple workload manager in
   :git_url:`klayout_package/python/scripts/simulations/elmer/scripts/simple_workload_manager.py`.

The simulation scripts are then prepared in a subfolder (for example `\$KQC_TMP_PATH/waveguides_sim_elmer` in the
affore mentioned example. The `$KQC_TMP_PATH` folder (is normally in `../tmp/`, remember to set it! If you do not,
you might get a read-only error when the singularity image tries to write to the image tmp folder that is
*read-only*)

In order to run the actual simulations, run::

  ./simulation.sh

.. note::
    Note that now Gmsh and Elmer are run in the container so no need to install the software.
