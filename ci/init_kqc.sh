#!/bin/sh
mkdir -p "$HOME"/.klayout/python .pip-cache
python -m pip install -r klayout_package/python/requirements/linux/pip-requirements.txt
pip-sync klayout_package/python/requirements/linux/requirements.txt \
    klayout_package/python/requirements/linux/doc-requirements.txt \
    klayout_package/python/requirements/linux/test-requirements.txt --pip-args "--cache-dir=.pip-cache"
ret=$?
if [ $ret -ne 0 ]; then
    echo "Can't install KQCircuits: pip-sync failed"
    exit $ret
fi
pip --cache-dir=.pip-cache install --no-deps -e "klayout_package/python/"
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
