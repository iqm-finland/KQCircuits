#!/bin/sh
mkdir -p "$HOME"/.klayout/python .pip-cache
pip --cache-dir=.pip-cache install -e "klayout_package/python[docs,tests]"
python setup_within_klayout.py
