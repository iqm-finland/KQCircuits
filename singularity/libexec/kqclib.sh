#!/bin/bash
dir="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
img="kqclib"
if [ "$(basename "$0")" = "kqclib" ]; then
	cmd="python"
else
	cmd=$(basename "$0")
fi
echo running: singularity exec --home "$HOME" "${dir}/${img}" "$cmd" "$@"
singularity exec --home "$HOME" "${dir}/${img}" "$cmd" "$@"
