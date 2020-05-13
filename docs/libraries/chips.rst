Chips
=====

AirbridgeCrossings
------------------

.. kqc_elem_params:: kqcircuits.chips.airbridge_crossings.AirbridgeCrossings.PARAMETERS_SCHEMA

Chip
----

Base class for all chips. Etching away the metal for dicing track, standard labels in the four
corners.

.. kqc_elem_params:: kqcircuits.chips.chip.Chip.PARAMETERS_SCHEMA

**Origin:** Center of the cross.

.. image:: ../images/chips/chipbase.png
    :alt: chipbase

Demo
----

.. kqc_elem_params:: kqcircuits.chips.demo.Demo.PARAMETERS_SCHEMA

JunctionTest
---------------------

.. kqc_elem_params:: kqcircuits.chips.junction_test.JunctionTest.PARAMETERS_SCHEMA

JunctionTest2
---------------------

.. kqc_elem_params:: kqcircuits.chips.junction_test2.JunctionTest2.PARAMETERS_SCHEMA

MultiFace
------------------

Base class for multi-face chips.

Produces labels in pixel corners, dicing edge and markers for all chip faces. Optionally can also produce
launchers in "b"-face, connectors between "b" and "t" faces, and default routing waveguides from the launchers to
the connectors.

.. kqc_elem_params:: kqcircuits.chips.multi_face.multi_face.MultiFace.PARAMETERS_SCHEMA

QualityFactor
---------------------

.. kqc_elem_params:: kqcircuits.chips.quality_factor.QualityFactor.PARAMETERS_SCHEMA

Shaping
---------------------

.. kqc_elem_params:: kqcircuits.chips.shaping.Shaping.PARAMETERS_SCHEMA




