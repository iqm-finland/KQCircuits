#!/bin/sh
Xvfb :99 -screen 0 640x480x24 &
if klayout -e -z -nc -r "$@" ; then
  echo "Succeeded in running KQCircuits."
else
  echo "KQCircuits failed to run. See https://iqm-finland.github.io/KQCircuits/developer/containers.html for instructions".
fi
