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
a standalone python module. For the first time users,
the graphical user interface (GUI) mode is recommended.

Video tutorials for the GUI installation can be found on YouTube.

.. raw:: html

   <div style="overflow:auto;">
     <table style="">
       <tr>
         <th>
           Windows
         </th>
         <th>
           Ubuntu
         </th>
         <th>
           MacOS
         </th>
       </tr>
       <tr>
         <th>
           <a href="https://youtu.be/9ra_5s2i3eU">
             <img src="https://img.youtube.com/vi/9ra_5s2i3eU/mqdefault.jpg" width=300 alt="KQCircuits Getting Started (Windows)">
           </a>
         </th>
         <th>
           <a href="https://youtu.be/ml773WtfnT0">
             <img src="https://img.youtube.com/vi/ml773WtfnT0/mqdefault.jpg" width=300 alt="KQCircuits Getting Started (Ubuntu)">
           </a>
         </th>
         <th>
           <a href="https://youtu.be/lt5ThOQ-caU">
             <img src="https://img.youtube.com/vi/lt5ThOQ-caU/mqdefault.jpg" width=300 alt="KQCircuits Getting Started (MacOS)">
           </a>
         </th>
       </tr>
     </table>
   </div>


Install GUI
^^^^^^^^^^^

`First install KLayout <https://www.klayout.de/build.html>`__.
Afterwards you can install KQCircuits as a plug-in to use KQCircuits features
within your KLayout GUI editor session.

Salt installation
"""""""""""""""""

To quickly try out KQCircuits GUI features we recommend installing the Salt package of KQCircuits
inside your KLayout application.
The Salt package is easier to install and get started, but the built-in elements cannot be modified.
`See Salt installation guide here  <https://iqm-finland.github.io/KQCircuits/salt.html>`__.

Developer setup
"""""""""""""""

The developer setup is recommended for advanced users who want to modify KQCircuits code and to contribute to the project.

After installing KLayout run:

.. code-block:: console

   python setup_within_klayout.py

For further details see the `developer setup
documentation <https://iqm-finland.github.io/KQCircuits/developer/setup.html>`__.

Install standalone python module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Installing KQCircuits as a standalone python module allows you to use KQCircuits features
in your own python code with:

.. code-block:: console

   import kqcircuits

You will also get access to kqc related terminal commands such as:

.. code-block:: console

   kqc mask quick_demo.py              # To build a wafer mask, in this case quick_demo.py
   kqc sim waveguides_sim_compare.py   # To export and run waveguide simulation

For standalone installation run command

.. code-block:: console

   python -m pip install -e "klayout_package/python[docs,tests,sim]"

For improved security you can also validate the fetched dependencies of KQCircuits.
Further details available in the `documentation
<https://iqm-finland.github.io/KQCircuits/developer/standalone.html>`__.

Documentation
-------------

Documentation for KQCircuits can be found `here <https://iqm-finland.github.io/KQCircuits/>`__.

It may also be generated from the sources with ``make html`` in the docs directory.

Tutorials
^^^^^^^^^

Follow the `User Guide <https://iqm-finland.github.io/KQCircuits/user_guide/index.html>`__ for tutorials.

.. image:: /docs/images/gui_workflows/converting_gui_elements_to_code.gif
   :target: https://iqm-finland.github.io/KQCircuits/user_guide/gui_features.html#converting-elements-placed-in-gui-into-code
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
<https://www.meetiqm.com/technology/iqm-kqcircuits#iqm-contributor-license-agreement>`__.
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

Copyright (C) 2021-2024 IQM Finland Oy

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
