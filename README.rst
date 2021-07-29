.. image:: /docs/images/logo-small.png
   :target: https://github.com/iqm-finland/KQCircuits
   :alt: KQCircuits
   :width: 300
   :align: center

**KQCircuits** is a Python library developed by IQM for automating the design of
superconducting quantum circuits. It uses the `KLayout <https://klayout.de>`__ layout design program
API.

.. image:: https://github.com/iqm-finland/KQCircuits/actions/workflows/ci.yaml/badge.svg
   :target: https://github.com/iqm-finland/KQCircuits/actions/workflows/ci.yaml
   :alt: Continuous Integration

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.4944796.svg
   :target: https://doi.org/10.5281/zenodo.4944796
   :alt: DOI

.. image:: https://img.shields.io/badge/License-GPLv3-blue.svg
   :target: https://github.com/iqm-finland/kqcircuits/blob/master/LICENSE
   :alt: License

.. image:: https://img.shields.io/github/v/tag/iqm-finland/KQCircuits?label=version&sort=semver
   :target: https://github.com/iqm-finland/KQCircuits/releases/
   :alt: Latest version

----

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

Install and run KLayout once. Run ``python3 setup_within_klayout.py`` then klayout will contain
KQCircuits. For further details see the `getting started documentation
<https://iqm-finland.github.io/KQCircuits/start/index.html>`__.

For stand-alone mode run ``python -m pip install -e klayout_package/python[docs,tests]``. Then scripts may be run and
documentation can be built. For further details see the `documentation
<https://iqm-finland.github.io/KQCircuits/developer/setup.html>`__.

Documentation
-------------

Documentation for KQCircuits can be found `here <https://iqm-finland.github.io/KQCircuits/>`__.

It may also be generated from the sources with ``make html`` in the docs directory.

Support
-------

If you have any questions, problems or ideas related to KQCircuits, please start
a
`discussion in GitHub <https://github.com/iqm-finland/KQCircuits/discussions>`__
or create a `GitHub issue <https://github.com/iqm-finland/KQCircuits/issues>`__.

Contributing
------------

Contributions to KQC are welcome from the community. Contributors are expected to accept IQM
Individual Contributor License Agreement by filling `a form at IQM website
<https://meetiqm.com/developers/clas>`__. See also section `Contributing
<https://iqm-finland.github.io/KQCircuits/developer/contributing.html>`__ in the
documentation.

Copyright
---------

This code is part of KQCircuits

Copyright (C) 2021 IQM Finland Oy

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see
https://www.gnu.org/licenses/gpl-3.0.html.

The software distribution should follow IQM trademark policy for open-source software
(meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).

Trademarks
----------

KQCircuits is a registered trademark of IQM. Please see
`IQM open source software trademark policy <https://meetiqm.com/developers/osstmpolicy>`__.
