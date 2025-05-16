.. _docker_image:

Containers
==========

A Docker image for CLI and CI usage is included in :git_url:`ci/Dockerfile`.

The image can be built manually from the root of the repository with ``-f ci/Dockerfile``.
Additionally, the KLayout version can be specified with ``--build-arg`` options by
providing the name of the KLayout package as ``KL_FILE`` and its MD5 hash as ``KL_HASH``::

  docker build -t kqcircuits -f ci/Dockerfile --build-arg KL_FILE=klayout_0.30.1-1_amd64.deb --build-arg KL_HASH=11953ce5009a0e83f9840b506f80df49 .

See possible versions and hashes for Ubuntu 22 in the `KLayout website <https://www.klayout.de/build.html>`_.


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

Singularity images are like docker images that work better
in HPC environments. Singularity images are managed using apptainer (https://apptainer.org/).
The latest image of a KQCircuits compatible Elmer installation can be downloaded from the
`GitHub Container registry <https://github.com/iqm-finland/KQCircuits/pkgs/container/kqcircuits/397719722?tag=main-singularity>`__.
Sinularity images can be pulled to Linux operating systems and also to Windows Subsystem for Linux (WSL).

Install apptainer (substituting 1.4.0 to whatever version is the most recent)::

   wget https://github.com/apptainer/apptainer/releases/download/v1.4.0/apptainer_1.4.0_amd64.deb
   sudo dpkg -i apptainer_1.4.0_amd64.deb

You might need to install other dependencies, like ``uidmap``.

Singularity image for KQCircuits should be downloaded to a ``libexec`` folder
under :git_url:`singularity` with the name ``kqclib``. The image size is about 1.4 Gb.
For WSL users, pay attention whether KQCircuits is cloned to a Windows drive or WSL's own drive.
At the root of the KQCircuits repository, pull the image with::

   singularity pull singularity/libexec/kqclib oras://ghcr.io/iqm-finland/kqcircuits:main-singularity

To check that the Singularity image was pulled correctly, run::

   singularity shell singularity/libexec/kqclib

It will open a shell: ``Singularity>``. In that shell run ``ElmerSolver``. It should give you an error,
but if you see ``ElmerSolver finite element software, Welcome!``, you have the singularity image pulled correctly.
Type ``exit`` to exit the singularity shell.

Next, cd to :git_url:`singularity` folder and run::

   ./create_links.sh

This will link the executables from the image rather than using the executables installed in your own system.

Then you need to add ``path-to-your-KQCircuits/singularity/bin`` to your ``$PATH`` environment variable.
In WSL, for example, this is done by adding to the end of ``~/.bashrc`` file a line::

   export PATH=path-to-your-KQCircuits/singularity/bin:$PATH

Then (if you haven't already) follow the Standalone installation guide :ref:`standalone`,
including ``simulations`` or ``sim-requirements.txt`` requirements. Notice that for WSL, a separate
`"venv" <https://docs.python.org/3/library/venv.html>`__ virtual environment needs to be created for WSL terminal.

Thats it! Try running ``kqc sim waveguide_sim_compare.py`` to see that it runs the simulations.

If you want to build the Singularity image yourself, in the :git_url:`singularity` folder run::

   ./singularity.sh
   ./create_links.sh

.. note::
    If a ``singularity.pem`` RSA public key is present in the ``singularity`` folder then the image will be encrypted. To
    successfully use this image the user also needs the corresponding ``$HOME/singularity_private.pem`` private key. See
    the `Singularity docs <https://docs.sylabs.io/guides/3.4/user-guide/encryption.html>`_ for further details.

Among other executables, the Singularity image contains the following executables that are needed for the simulation workflow::

   EXECUTABLES=("ElmerSolver" "ElmerSolver_mpi" "ElmerGrid" "klayout" "kqclib" "python")

You could add your own executable in the list in ``create_links.sh`` (it is just a symbolic link 
named like the executable that then needs to be found in the image).

.. note::
   python is not put in $PWD/bin such that it does not over-ride the system python even if the 
   folder is added to PATH environment variable"

.. note::
   In ``waveguides_sim_compare.py``, one has to set ``workflow['python_executable']='kqclib'`` or 
   ``workflow['python_executable']='path-to-your-KQCircuits/singularity/python'`` (in order to use
   the singularity image or override the system python with the latter executable, by moving it
   to path-to-your-KQCircuits/singularity/bin). 

.. warning::
   It is difficult to set up `Paraview <https://www.paraview.org/>`__ to work in a WSL environment.
   We recommend not to bother with it, and to view the ``*.pvtu/*.vtu`` results manually in
   native Windows environment after simulation execution.
