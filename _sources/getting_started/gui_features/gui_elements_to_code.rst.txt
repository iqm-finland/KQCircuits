.. _gui_elements_to_code:

Converting elements placed in GUI into code
===========================================

KQCircuits includes a macro :git_url:`export_cells_as_code.lym <klayout_package/python/scripts/macros/export/export_cells_as_code.lym>` that can be used to
convert elements placed in GUI into code that can be used in chip PCells. For
more information, see the docstring and comments in the macro. The following
animation demonstrates how a chip is modified by placing elements in the GUI
and how to use this macro to include those elements in PCell generation code:

.. image:: ../../images/gui_workflows/converting_gui_elements_to_code.gif

The macro has special handling for waveguides (of :class:`.WaveguideCoplanar` type).
The code generated for them automatically detects nearby reference points of
other elements, and uses these instead of hardcoded points as the positions
of the waveguide nodes. See the :ref:`modifying_waveguides` section above for
instructions on how to modify :class:`.WaveguideCoplanar` in GUI.

In order to make waveguides connect "nicely" to ports of other elements, most
ports in KQC elements have an additional "corner refpoint". To connect a
waveguide to port "a" of instance "x", you  should generally place its first
two points at ``x_port_a`` and ``x_port_a_corner``. The corner point is not
needed if the next point would anyway be in the direction of
``x_port_a_corner``, since the purpose of the corner point is only to make
the direction of the first waveguide segment aligned with the port.
