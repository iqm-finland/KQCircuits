.. _elmer_remote_workflow:

Elmer remote simulations workflow
=================================

Elmer simulations can be run on a remotely on a computing cluster using SLURM workload manager. 
Below are some steps on how to get started with the workflow

See :ref:`gmsh_elmer_export`. for explanation of the Slurm settings controlling the amount of computing resources requested

Setup:

1. Add ssh-key without password on the remote
2. Build and push singularity image to the remote using
    2.1. ``kqc singularity --build``: Compile singularity image
       The desired package versions such as OpenMPI can be chosen by modifying
       the definitions in the beginning of ``KQCircuits/singularity/install_software.sh`` script
       (**NOTE that MPI implementation and its version has to match those of the remote machine!**).
    2.2. ``kqc singularity --push user@host``: Send singularity image to remote and setup symbolic links. 
       You can directory choose the remote directory by specifying ``--singularity-remote-path SINGULARITY_PATH``.
       By default uses ``user@host:~/KQCircuits/singularity``. 
3. Add ``user@host:SINGULARITY_PATH/bin`` to the PATH on your bash profile on remote
4. When running simulations, make sure the export script has ``workflow['sbatch_parameter']`` defined and the account field is 
   modified to have correct project. The account can be also set in a local environment variable ``KQC_REMOTE_ACCOUNT`` such that 
   it is not needed separately in each export script

Running the simulations::

    kqc sim --remote user@host sim_1.py sim_2.py ...

You can also export and run with separate commands, but export exporting with ``kqc sim -e`` is only supported 
for a single simulations script at a time::

    kqc sim sim_1.py -e
    ...
    kqc sim sim_n.py -e
    kqc sim --remote-run-only user@host sim_1... sim_n

On local machine the default export folder name is the same as the export script name without the ``.py`` extension, which 
can be changed with ``--export-path-basename`` option. On remote machine the name of the export folder cannot be modified, 
but the path where it's copied can with the option ``--kqc-remote-tmp-path``, which defaults to ``~/KQCircuits/tmp/``. There is also
a possibility to override this default by setting a local environment variable ``KQC_REMOTE_TMP_PATH``, which will be used instead.


The simulations are run in the background such that a script on the local machine polls the the remote via ssh for
job state and automatically copies the results back once the simulation is finished. The polling interval in seconds
can be determined with the option ``--poll-interval``. The output of the polling script can be detached from the current
terminal with ``--detach`` option in which case the output is saved to a ``sim_i_tmp_folder/../nohup_runid.out`` file,
where ``runid`` is an unique run identifier. This can be followed for example with ``watch cat sim_i_tmp_folder/../nohup_runid.out``


.. note:: 

    Only simulations in the folder ``KQCircuits/klayout_package/python/scripts/simulations`` 
    can be exported and only exported simulations from ``KQCircuits/tmp`` can be copied and run on remote. 