KQCircuits
===============

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

There are two different ways to use KQCircuits:

#. Use with KLayout Editor.
#. Use with standalone KLayout Python module.

For any of these use cases, you should git clone the repository from
https://github.iqm.fi/iqm/KQCircuits to a local directory of your choice.

KQCircuits with KLayout Editor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

KQCircuits objects, such as elements and chips, can be viewed and manipulated
in the KLayout Editor GUI. More complicated tasks in KLayout Editor can be
done by writing KLayout macros, which use the KQCircuits library. The code runs
within KLayout's built-in Python interpreter, so debugging must be done in
KLayout's macro IDE.

For instructions on installation and basic usage, see the `documentation
<https://pages.github.iqm.fi/iqm/KQCircuits/_build/html/start/klayout_editor.html>`__.

KQCircuits with standalone KLayout Python module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

KQCircuits can be used without KLayout Editor by using the standalone KLayout
Python module. This lets you develop and use KQCircuits completely within any
Python development environment of your choice, without running KLayout GUI.
For example, any debugger can then be used and automated tests can be performed.
The KQCircuits elements can also be visualized using any suitable viewer or
library during development.

For instructions on installation and basic usage, see the `documentation
<https://pages.github.iqm.fi/iqm/KQCircuits/_build/html/start/klayout_standalone.html>`__.

Documentation
-------------

Documentation for KQCircuits can be found `here <https://pages.github.iqm.fi/iqm/KQCircuits>`__.

Copyright
---------

Copyright (c) 2019-2020 IQM Finland Oy.

All rights reserved. Confidential and proprietary.

Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy's prior written permission.
