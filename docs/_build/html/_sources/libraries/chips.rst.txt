Chips
=====

AirbridgeCrossings
------------------

.. kqc_elem_params:: kqcircuits.chips.airbridge_crossings

AirbridgeDcTest
------------------

Chip full of airbridge 4-point dc tests.

.. kqc_elem_params:: kqcircuits.chips.airbridge_dc_test

.. image:: ../images/chips/airbridge_dc_test.png
    :alt: airbridge_dc_test

Chip
----

Base class for all chips. Etching away the metal for dicing track, standard labels in the four
corners.

.. kqc_elem_params:: kqcircuits.chips.chip

**Origin:** Center of the cross.

.. image:: ../images/chips/chipbase.png
    :alt: chipbase

DaisyWoven
----------

.. kqc_elem_params:: kqcircuits.chips.multi_face.daisy_woven

.. image:: ../images/chips/multi_face/daisy_woven.png
    :alt: daisy_woven

Demo
----

.. kqc_elem_params:: kqcircuits.chips.demo

Empty
-----
Chip with almost all ground metal removed, used for EBL tests.

.. kqc_elem_params:: kqcircuits.chips.empty

.. image:: ../images/chips/empty_chip.png
    :alt: empty_chip

JunctionTest
---------------------

.. kqc_elem_params:: kqcircuits.chips.junction_test

JunctionTest2
---------------------

.. kqc_elem_params:: kqcircuits.chips.junction_test2

LithographyTest
---------------------

.. kqc_elem_params:: kqcircuits.chips.lithography_test

.. image:: ../images/chips/lithography_test.png
    :alt: lithography_test

MultiFace
------------------

Base class for multi-face chips.

Produces labels in pixel corners, dicing edge and markers for all chip faces. Optionally can also produce
launchers in "b"-face, connectors between "b" and "t" faces, and default routing waveguides from the launchers to
the connectors.

.. kqc_elem_params:: kqcircuits.chips.multi_face.multi_face

CrossingTwoface
----------------

Base class for CrossingTwoface chips. The left part of the chip has variable number of crossings between a transmission
line on the horizontal direction and top-face transmission line on vertical direction. The right part of the circuit
represents non-crossing transmission lines.

.. kqc_elem_params:: kqcircuits.chips.multi_face.crossing_twoface

.. image:: ../images/chips/multi_face/crossing_twoface.png
    :alt: quality_factor_twoface

QualityFactorTwoface
--------------------

Base class for QualityFactorTwoface chips. Preliminary design which is going to be changed.

.. kqc_elem_params:: kqcircuits.chips.multi_face.quality_factor_twoface

.. image:: ../images/chips/multi_face/quality_factor_twoface.png
    :alt: crossing_twoface

QualityFactor
---------------------

.. kqc_elem_params:: kqcircuits.chips.quality_factor

Shaping
---------------------

.. kqc_elem_params:: kqcircuits.chips.shaping

SingleXmons
---------------------

The SingleXmons chip has 6 qubits, which are coupled by readout resonators to the same feedline. The feedline
crosses the center of the chip horizontally.  Half of the qubits are above the feedline and half are below it.
For each qubit, there is a chargeline connected to a launcher, but no fluxline. There can optionally be four test
resonators between the qubits.

.. kqc_elem_params:: kqcircuits.chips.single_xmons

.. image:: ../images/chips/single_xmons_chip.png
    :alt: single_xmons_chip

Stripes
---------------------

.. kqc_elem_params:: kqcircuits.chips.stripes

XmonsDirectCoupling
---------------------

.. kqc_elem_params:: kqcircuits.chips.xmons_direct_coupling