KQCircuits
==========

KQCircuits is a Python library developed by IQM for automating the design of
superconducting quantum circuits. It uses the `KLayout
<https://klayout.de>`__ layout design program API. KQCircuits contains elements
and chips which can be combined in different ways to create mask designs for the
quantum circuits. The elements are parameterized so that different variants
can quickly be created either in the KLayout GUI or in code.

.. image:: /docs/images/readme/single_xmons_chip_3.png
    :alt: example layout
    :align: center

Getting started
---------------

KQCircuits is a KLayout extension. KLayout can be used either using a graphical
user interface or as a standalone python module. KQCircuits supports both modes
of operation. For the first time users, the graphical user interface mode is
recommended.  To get started with graphical user interface workflow, see the
`getting started documentation
<https://pages.github.iqm.fi/iqm/KQCircuits/docs/_build/html/start/index.html>`__
for instructions on installation and usage of KQC with the KLayout Editor.

To use KQC without KLayout graphical user interface, use it with the standalone
KLayout python module. For instructions on that, see the `documentation
<https://pages.github.iqm.fi/iqm/KQCircuits/docs/_build/html/developer/klayout_standalone.html>`__.

Documentation
-------------

Documentation for KQCircuits can be found `here <https://pages.github.iqm.fi/iqm/KQCircuits>`__.

Copyright
---------

Copyright (c) 2019-2020 IQM Finland Oy.

All rights reserved. Confidential and proprietary.

Distribution or reproduction of any information contained herein is prohibited
without IQM Finland Oy's prior written permission.
