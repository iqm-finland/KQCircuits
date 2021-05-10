KQCircuits
==========

KQCircuits is a Python library developed by Aalto and IQM for automating the design of
superconducting quantum circuits. It uses the `KLayout <https://klayout.de>`__ layout design program
API.

KQCircuits generates multi-layer 2-dimensional-geometry representing common structures in quantum
processing units (QPU). It includes definitions of parametrized geometrical objects or “elements”,
framework to easily define your own elements, framework to get geometry from the elements by setting
values to parameters and a framework to assemble a full QPU design by combining many of the elements
in different geometrical relations. Among other templates, are also structures to combine QPU
designs to create optical mask layout and EBL patterns for fabrication of quantum circuits and
export a set of files for a mask as needed for QPU fabrication.

.. image:: /docs/images/readme/single_xmons_chip_3.png
    :alt: example layout
    :align: center

Getting started
---------------

KQCircuits is a KLayout extension. KLayout can be used either using a graphical user interface or as
a standalone python module. KQCircuits supports both modes of operation. For the first time users,
the graphical user interface mode is recommended.

Install and run KLayout once. Run `python3 setup_within_klayout.py` then klayout will contain
KQCircuits. For further details see the `getting started documentation
<https://iqm.gitlab-pages.iqm.fi/qe/KQCircuits/start/index.html>`__.

For stand alone mode run `python -m pip install -e .[docs,tests]`. Then scripts may be run and
documentation can be built. For further details see the `documentation
<https://iqm.gitlab-pages.iqm.fi/qe/KQCircuits/developer/setup.html>`__.

Documentation
-------------

Documentation for KQCircuits can be found `here <https://iqm.gitlab-pages.iqm.fi/qe/KQCircuits/>`__.

It may also be generated from the sources with `make html` in the docs directory.

Copyright
---------

Copyright (c) 2019-2021 IQM Finland Oy.

All rights reserved. Confidential and proprietary.

Distribution or reproduction of any information contained herein is prohibited without IQM Finland
Oy's prior written permission.
