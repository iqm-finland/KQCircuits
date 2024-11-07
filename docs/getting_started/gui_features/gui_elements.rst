Placing Elements
================

There are two ways to insert an ``Element`` into the layout:

#. dragging from **Libraries** toolbox

#. using "instance" tool from the toolbar

Either of these will generate the corresponding **PCell** and allows you to place an **Instance** of the PCell in
If the corresponding **PCell instance** does not yet exist, corresponding code from the KQC library is evoked.

Here is an animation demonstrating dragging from the **Libraries** toolbox

.. image:: ../../images/gui_workflows/placing_pcell.gif

Modifying Element parameters
----------------------------

If an ``Element`` is in the layout, one can change its **parameters** by double clicking the ``Element`` which brings up
the **Object properties** window. In the window there is a **PCell parameters** tab, where parameters can be changed.

.. image:: ../../images/gui_workflows/modifying_pcell.gif

Note that there are a few situations where the *Object properties* window doesn't appear when double clicking:

* The ``Element`` is inside another PCell. One can only change parameters of the top level Element. If one desires to
  change parameters of the sub-elements, the top level element should be turned static before by selecting the top
  level element and clicking *Edit* -> *Selection* -> *Convert To Static Cell*. Then, the cell can be set as new top
  in the Cells toolbox.
* Once an ``Element`` is converted to a static cell, the parameters can no longer be changed.
* Some elements have guiding shapes such as boxes or paths, which take priority in selection. To avoid selecting these
  by accident, one can disable each type under *Edit* -> *Select*.
