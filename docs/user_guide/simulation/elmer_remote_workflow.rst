.. _elmer_remote_workflow:

Elmer remote simulations workflow
=================================

Elmer simulations can be run on a remotely on a computing cluster using SLURM workload manager. 
Below are some steps on how to get started with the workflow

See :ref:`gmsh_elmer_export`. for explanation of the Slurm settings controlling the amount of computing resources requested

Setup:

* Add your ssh-key to the remote
* Build and push singularity image to the remote using
    * `kqc singularity --build`: Compile singularity image
       The desired package versions such as OpenMPI can be chosen by modifying
       the definitions in the beginning of `KQCircuits/singularity/install_software.sh` script
       (**NOTE that MPI implementation and its version has to match those of the remote machine!**).
    * `kqc singularity --push user@host`: Send singularity image to remote and setup symbolic links. 
       You can directory choose the remote directory by specifying `--singularity-remote-path SINGULARITY_PATH`.
       By default uses `user@host:~/KQCircuits/singularity`. 
* Make sure that `user@host:SINGULARITY_PATH/bin` is added to the PATH when using login shell on remote
* Make sure the export script has `workflow['sbatch_parameter']` defined and the account field is modified to have correct project

Run simulations:

- In 1 step:

    - `kqc sim --remote user@host sim_1.py sim_2.py ...`
- Or in 2 steps:

    * for each n simulations: `kqc sim sim_i.py -e --export-path-basename sim_i_tmp_folder`
    * `kqc sim --remote-run-only user@host sim_1_tmp_folder... sim_n_tmp_folder`

- The simulations can be run on background with `--detach` flag in which case the output is saved to a `sim_i_tmp_folder/../nohup_runid.out` file, 
  where `runid` is an unique run identifier. This can be followed for example with `watch cat sim_i_tmp_folder/../nohup_runid.out`

.. note:: 

    Simulations need an empty folder on remote that will be cleared once all simulations are finsihed. By default `~/KQCircuits/tmp` is used, 
    but this can be changed by using option `--kqc-remote-tmp-path KQC_REMOTE_TMP_PATH` with commands `kqc sim --remote-run-only` and `kqc sim --remote` 

.. note:: 

    Only simulations in the folder `KQCircuits/klayout_package/python/scripts/simulations` 
    can be exported and exported simulations from `KQCircuits/tmp` can be copied and run on remote. 