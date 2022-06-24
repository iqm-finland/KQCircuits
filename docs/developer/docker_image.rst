.. _docker_image:

Docker image
============

A Docker image for CLI and CI usage is included in `ci/Dockerfile <https://github.com/iqm-finland/KQCircuits/blob/main/ci/Dockerfile>`_.

CLI usage
---------

The image can be used to quickly generate files, such as masks and chips from Python scripts.
For example, to run a script ``m00x.py`` from a local directory, do the following::

   docker run --volume ${PWD}:/kqc/tmp ghcr.io/iqm-finland/kqcircuits:main tmp/m00x.py


This runs the script in a Docker container and on-default writes the output to ``/kqc/tmp``,
which is mounted to the working directory with ``--volume``.
More specifically, it executes the following command in `ci/run_script.sh <https://github.com/iqm-finland/KQCircuits/blob/main/ci/run_script.sh>`_::

   klayout -e -z -nc -rx -r tmp/m00x.py


Additional arguments can of course be given, such as variables through ``-wd <name>=<value>``.
See `CLI arguments for KLayout <https://www.klayout.de/command_args.html>`_ for more info.

.. note::
    If the script imports code like elements not included in KQCircuits,
    your local KQCircuits environment should be mounted to overwrite the one in the container.
    To this end, simply mount ``/kqc``.

If using the older HyperV backend on Windows, you might need to increase your RAM limit from the 1GB default depending on your usage. 
See `Docker Runtime options with Memory <https://docs.docker.com/config/containers/resource_constraints/#limit-a-containers-access-to-memory>`_ for details.

To override `ci/run_script.sh <https://github.com/iqm-finland/KQCircuits/blob/main/ci/run_script.sh>`_ entirely, you can use the `Docker entrypoint argument <https://docs.docker.com/engine/reference/run/#entrypoint-default-command-to-execute-at-runtime>`_.

.. _docker_ci_usage:

CI usage
--------

The image is built and published automatically in the release workflow on version tags and pushes to the main branch.
It is then used to run all the tests in the CI pipeline.

Pull requests build the image but do not push it to the registry so that the changes may be tested to see
whether they break the image.
