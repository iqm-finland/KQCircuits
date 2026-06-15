#!/bin/sh
mkdir -p "$HOME"/.klayout/python .pip-cache
# Using --break-system-packages looks scary.
# Python encourages to install pip packages on a dedicated virtual environment.
# For CI this causes headaches that I'd rather not deal with,
# so for simplicity we force the installation to "system" python
# since this script is only intended to be executed by a Docker image.
python -m pip install --cache-dir=.pip-cache --break-system-packages \
    -r klayout_package/python/requirements/linux/requirements.txt \
    -r klayout_package/python/requirements/linux/dev-requirements.txt \
    -r klayout_package/python/requirements/linux/sim-requirements.txt
ret=$?
if [ $ret -ne 0 ]; then
    echo "Can't install KQCircuits: installing requirements.txt failed"
    exit $ret
fi
pip --cache-dir=.pip-cache install --break-system-packages --no-deps -e "klayout_package/python/"
ret=$?
if [ $ret -ne 0 ]; then
    echo "Can't install KQCircuits: pip install --no-deps failed"
    exit $ret
fi
python setup_within_klayout.py
ret=$?
if [ $ret -ne 0 ]; then
    echo "Can't install KQCircuits: couldn't set it up for KLayout app"
    exit $ret
fi
