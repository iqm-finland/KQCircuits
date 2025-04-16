.. image:: /docs/images/logo-small.png
   :target: https://github.com/iqm-finland/KQCircuits
   :alt: KQCircuits
   :width: 300
   :align: center

**KQCircuits** is a Python library developed by IQM for automating the design of
superconducting quantum circuits. It uses the `KLayout <https://klayout.de>`__ layout design API.

.. image:: https://github.com/iqm-finland/KQCircuits/actions/workflows/ci.yaml/badge.svg
   :target: https://github.com/iqm-finland/KQCircuits/actions/workflows/ci.yaml
   :alt: Continuous Integration

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.4944796.svg
   :target: https://doi.org/10.5281/zenodo.4944796
   :alt: DOI

.. image:: https://img.shields.io/badge/License-GPLv3-blue.svg
   :target: https://github.com/iqm-finland/kqcircuits/blob/master/LICENSE
   :alt: License

.. image:: https://img.shields.io/pypi/v/kqcircuits
   :target: https://pypi.org/project/kqcircuits/
   :alt: PyPI Package

.. image:: https://img.shields.io/badge/click-for%20documentation%20%F0%9F%93%92-lightgrey
   :target: https://iqm-finland.github.io/KQCircuits/index.html
   :alt: Click for documentation

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Black badge

----

KQCircuits generates multi-layer 2-dimensional-geometry representing common structures in quantum
processing units (QPU). It includes definitions of parametrized geometrical objects or “elements”,
framework to easily define your own elements, framework to get geometry from the elements by setting
values to parameters and a framework to assemble a full QPU design by combining many of the elements
in different geometrical relations. Among other templates, are also structures to combine QPU
designs to create optical mask layout and EBL patterns for fabrication of quantum circuits and
export a set of files for a mask as needed for QPU fabrication.

.. image:: /docs/images/readme/design_flow.svg
   :alt: QPU design workflow
   :width: 700


.. image:: /docs/images/readme/single_xmons_chip_3.png
   :alt: Example layout

Getting started
---------------

KQCircuits is a KLayout extension. KLayout can be used either using a graphical user interface or as
a standalone python module. For first time users, the graphical user interface (GUI) mode is recommended.

To get a first introduction to KQCircuits, follow the
`Getting started tutorial <https://iqm-finland.github.io/KQCircuits/getting_started/index.html>`__. It will show you
how to install and use KQCircuits in the KLayout GUI, how to create your own custom elements and chips in python code,
and explains the basics of the KQCircuits workflow.

The following video shows some of the KQC features:

.. image:: https://img.youtube.com/vi/9ra_5s2i3eU/mqdefault.jpg
   :target: https://youtu.be/9ra_5s2i3eU
   :alt: KQCircuits Getting Started


Installation (Klayout GUI)
^^^^^^^^^^^^^^^^^^^^^^^^^^

`First install KLayout <https://iqm-finland.github.io/KQCircuits/installation/klayout.html>`__.
Then, KQCircuits can be installed in two ways:

* `As a Salt package directly from KLayout  <https://iqm-finland.github.io/KQCircuits/getting_started/salt.html>`__.
  This allows you to use the KQCircuits chips and elements, and create a user package for your own custom designs.
* Download the GIT repository, and follow the `Developer GUI setup <https://iqm-finland.github.io/KQCircuits/developer/setup.html>`__.
  Choose this if you want to modify the KQCircuits code and possibly contribute to the project.

You can always switch from Salt package to developer setup later on.

Installation as standalone python module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`Installing KQCircuits as a stand alone python module <https://iqm-finland.github.io/KQCircuits/developer/standalone.html>`__
allows you to use KQCircuits features in your own python code with:

.. code-block:: console

   import kqcircuits

You will also get access to kqc related terminal commands such as:

.. code-block:: console

   kqc mask quick_demo.py              # To build a wafer mask, in this case quick_demo.py
   kqc sim waveguides_sim_compare.py   # To export and run waveguide simulation

For standalone installation run command

.. code-block:: console

   python -m pip install -e "klayout_package/python[docs,tests,sim]"

Further details available in the `documentation <https://iqm-finland.github.io/KQCircuits/developer/standalone.html>`__.

Documentation
-------------

Documentation for KQCircuits can be found `here <https://iqm-finland.github.io/KQCircuits/>`__.

It may also be generated from the sources with ``make html`` in the docs directory.

Tutorials
^^^^^^^^^

Follow the `Getting started <https://iqm-finland.github.io/KQCircuits/getting_started/index.html>`__ section for tutorials.

.. image:: /docs/images/gui_workflows/converting_gui_elements_to_code.gif
   :target: https://iqm-finland.github.io/KQCircuits/getting_started/gui_features/gui_elements_to_code.html
   :alt: Example of GUI elements
   :width: 600

Simulations
-----------

.. image:: /docs/images/readme/xmon_animation.gif
   :alt: Animation of simulations
   :width: 350

KQC currently supports exporting to **Ansys HFSS/Q3D (also with pyEPR)**, **Sonnet**, and **Elmer**.

Parameter sweeps are easy to implement, for example

.. code-block:: python

   simulations = sweep_simulation(layout, sim_class, sim_parameters, {
       'cpl_length': [160, 180, 200],
       'arm_width': [24, 28, 32, 36],
   })

exports simulations with the given individual parameters varied roughly as in the animation.

A sweep of all possible combinations between the given parameters is done by changing the function to
``cross_sweep_simulation``.
Check `klayout_package/python/scripts/simulations <https://github.com/iqm-finland/KQCircuits/tree/main/klayout_package/python/scripts/simulations>`__
for example simulation exports.

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
<https://www.meetiqm.com/technology/iqm-kqcircuits/iqm-individual-contributor-license-agreement/>`__.
See also section `Contributing
<https://iqm-finland.github.io/KQCircuits/contributing.html>`__ in the
documentation.

Citation
--------
Please see the
`documentation <https://iqm-finland.github.io/KQCircuits/citing.html>`__
for instructions on how to cite KQCircuits in your projects and publications.

Copyright
---------

This code is part of KQCircuits

Copyright (C) 2021-2025 IQM Finland Oy

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see
https://www.gnu.org/licenses/gpl-3.0.html.

The software distribution should follow IQM trademark policy for open-source software
(`meetiqm.com/iqm-open-source-trademark-policy <https://meetiqm.com/iqm-open-source-trademark-policy/>`__).
IQM welcomes contributions to the code. Please see our contribution agreements for individuals
(`meetiqm.com/iqm-individual-contributor-license-agreement <https://meetiqm.com/iqm-individual-contributor-license-agreement/>`__)
and organizations (`meetiqm.com/iqm-organization-contributor-license-agreement <https://meetiqm.com/iqm-organization-contributor-license-agreement/>`__).

Trademarks
----------

KQCircuits is a registered trademark of IQM. Please see
`IQM open source software trademark policy <https://meetiqm.com/iqm-open-source-trademark-policy>`__.
