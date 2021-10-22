Elements
========

Airbridge
-------------------------

Origin is at the geometric center. The airbridge is in vertical direction. There are multiple types of airbridges.

Normal:
Bottom parts of pads in bottom layer, bridge and top parts of pads in top layer. Pads and bridge are rectangular.
Refpoints "port_a" and "port_b" at top pad points closest to origin.

.. kqc_elem_params:: kqcircuits.elements.airbridges.airbridge

**Origin:** Center

.. image:: ../images/elements/airbridge_normal.png
    :alt: airbridge

ChipFrame
----------

The chip frame consists of a dicing edge, and labels and markers in the corners.

.. kqc_elem_params:: kqcircuits.elements.chip_frame

Element
-------

Base class for all elements.

.. kqc_elem_params:: kqcircuits.elements.element

FingerCapacitorSquare
---------------------

Two ports with reference points. The arm leading to the finger has the
same width as fingers. The feedline has the same length as the width of
the ground gap around the coupler.

.. kqc_elem_params:: kqcircuits.elements.finger_capacitor_square

**Origin:** Center

.. image:: ../images/elements/fingercaps.png
    :alt: fingercaps

FingerCapacitorTaper
--------------------

Two ports with reference points. Ground plane gap is automatically
adjusted to maintain the a/b ratio.

.. kqc_elem_params:: kqcircuits.elements.finger_capacitor_taper

**Origin:** Center

.. image:: ../images/elements/fingercapt.png
    :alt: fingercapt

Flip chip connector
-------------------

Dc connectors for flip-chip

.. kqc_elem_params:: kqcircuits.elements.f2f_connectors.flip_chip_connectors.flip_chip_connector_dc

.. image:: ../images/elements/flip_chip_dc.png
    :alt: flip_chip_dc

Flip chip connector Rf
----------------------

Radio frequency connectors for flip-chip

.. kqc_elem_params:: kqcircuits.elements.f2f_connectors.flip_chip_connectors.flip_chip_connector_rf

.. image:: ../images/elements/flip_chip_rf.png
    :alt: flip_chip_rf

TSV connector
-------------

Through silicon via geometry

.. kqc_elem_params:: kqcircuits.elements.f2f_connectors.tsvs.tsv

.. image:: ../images/elements/tsv.png
    :alt: tsv

Manual SQUIDs
-------------

These SQUIDs are manually drawn and automatically loaded from a library
file. SQUIDs are referred to by the Cell name in the library file.

.. image:: ../images/squids/qcd1.png
    :alt: qcd1
.. image:: ../images/squids/sim1.png
    :alt: sim1

Launcher
--------

Launcher for connecting wirebonds. Default wirebond direction to west,
waveguide to east. Uses default ratio ``a`` and ``b`` for scaling the
gap. Taper length is from waveguide port to the rectangular part of
the launcher pad. Pad width is also used for the length of the launcher pad.

.. kqc_elem_params:: kqcircuits.elements.launcher

**Origin:** Waveguide port

.. image:: ../images/elements/launcher.png
    :alt: launcher

LauncherDC
----------

DC launcher for connecting wirebonds.

.. kqc_elem_params:: kqcircuits.elements.launcher_dc

**Origin:** center

.. image:: ../images/elements/launcher_dc.png
    :alt: launcher_dc

Marker
------

.. kqc_elem_params:: kqcircuits.elements.markers.marker

MaskMarkerFc
------------

.. kqc_elem_params:: kqcircuits.elements.mask_marker_fc

Meander
-------

Defined by two points, total length and number of meanders. Uses the
same bending radius as the underling waveguide. Each perpendicular
segment is a meander.

.. kqc_elem_params:: kqcircuits.elements.meander

**Origin:** absolute position of ``start``

.. image:: ../images/elements/meander.png
    :alt: meander

SpiralResonatorRectangle
--------------------------

The input of the resonator (refpoint `base`) is at left edge of the resonator
. The space above, below, and right of the input are parameters, so the
resonator will be within a box right of the input. The resonator length is a
parameter, and it is attempted to be fit into the box such that the spacing
between waveguides is as large as possible.

.. kqc_elem_params:: kqcircuits.elements.spiral_resonator_rectangle

.. image:: ../images/elements/spiral_resonator.png
    :alt: spiral resonator

Swissmon
---------

Swissmon type qubit. Each arm (West, North, East, South) has it's own
width. "Hole" for the island has the same ``gap_width`` for each arm.
SQUID is loaded from another library. Option of having fluxline.
Refpoints for 3 couplers, fluxline position and chargeline position.
Length between the ports is from waveguide port to the rectangular part of the launcher pad.
Length of the fingers is also used for the length of the launcher pad.

.. kqc_elem_params:: kqcircuits.qubits.swissmon

**Origin:** Center of the cross.

.. image:: ../images/elements/swissmon.png
    :alt: swissmon

WaveguideCoplanar
-----------------

Coplanar waveguide defined by the width of the center conductor and gap.
It can follow any segmented lines with predefined bending radius. It
actually consists of straight and curved PCells. Termination lengths are lengths of extra ground
gaps for opened transmission lines

**Warning** Arbitrary angle bents actually have very small gaps between
bends and straight segments due to precision of arithmetic. To be fixed
in a future release.

**Parameters:**

.. kqc_elem_params:: kqcircuits.elements.waveguide_coplanar

**Origin:** One port or follows the absolute coordinates of the path.

.. image:: ../images/elements/waveguide.png
    :alt: waveguide

.. image:: ../images/elements/waveguide2.png
    :alt: waveguide2

WaveguideCoplanarCurved
-----------------------

.. kqc_elem_params:: kqcircuits.elements.waveguide_coplanar_curved

WaveguideCoplanarStraight
-------------------------

.. kqc_elem_params:: kqcircuits.elements.waveguide_coplanar_straight

WaveguideCoplanarTaper
----------------------

.. kqc_elem_params:: kqcircuits.elements.waveguide_coplanar_taper

.. image:: ../images/elements/waveguide_taper.png
    :alt: waveguide_taper

WaveguideCoplanarTCross
-----------------------

.. kqc_elem_params:: kqcircuits.elements.waveguide_coplanar_tcross
