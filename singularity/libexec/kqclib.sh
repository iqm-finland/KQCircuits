#!/bin/bash
dir="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
img="kqclib"
if [ "$(basename "$0")" = "kqclib" ]; then
	cmd="python"
else
	cmd=$(basename "$0")
fi

# Check if running on WSL and use higher compatibility then
if grep -qi "microsoft" /proc/version; then
  echo running: singularity exec --containall --home "${PWD}" "${dir}/${img}" "$cmd" "$@"
  singularity exec --containall --home "${PWD}" "${dir}/${img}" "$cmd" "$@"
else
  echo running: singularity exec --home "$HOME" "${dir}/${img}" "$cmd" "$@"
  singularity exec --home "$HOME" "${dir}/${img}" "$cmd" "$@"
fi
