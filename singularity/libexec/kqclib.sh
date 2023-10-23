#!/bin/bash
dir="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
img="kqclib"
if [ "$(basename "$0")" = "kqclib" ]; then
	cmd="python"
else
	cmd=$(basename "$0")
fi


if [ -e "$HOME/singularity_private.pem" ]; then
    run_cmd="singularity exec --pem-path=$HOME/singularity_private.pem"
else
    run_cmd="singularity exec"
fi

# Check if running on WSL and use higher compatibility then
if grep -qi "microsoft" /proc/version; then

  # -np n are given as 2 last arguments when using wsl and ElmeSolver
  # automated in run_elmer_solver in run_helpers.py
  if [ "$2" = "-np" ]; then
    single_cmd="mpirun $2 $3 $cmd $1"
  else
    # If in wsl but using other tool than ElmerSolver
    single_cmd="$cmd $*"
  fi
  run_cmd+=" --home ${PWD} ${dir}/${img} $single_cmd"
  echo running: "$run_cmd"
  $run_cmd
else
  run_cmd+=" --home ${PWD} ${dir}/${img} $cmd $*"
  echo running: "$run_cmd"
  $run_cmd
fi
