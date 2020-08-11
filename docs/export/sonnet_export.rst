Exporting to Sonnet
===================
Exporting to Sonnet is supported for up to one chip but generating .son files for larger geometry is increasingly slow due to the port-edge finding algorithm. In addition, processing in Sonnet becomes impractical due to huge amount of RAM needed. Simpler geometry is preferred. Airbridges are supported with Sonnet vias and auto-detected.

You can either detect all ports to be converted to Sonnet ports or convert only annotations containing the text *sonnet_port* for more control over the simulation environment. Set this with the `auto_port_detection` setting.

Instructions
------------

When you have an active project open, import the following and get the top cell and layout::

    from kqcircuits.klayout_view import KLayoutView
    from kqcircuits.simulations.simulation import Simulation
    from kqcircuits.simulations.sonnet.sonnet_export import SonnetExport

    top_cell = KLayoutView.get_active_cell()
    layout = KLayoutView.get_active_layout()

Set where you want your files. For example, the working directory could be set with ``import os; os.getcwd()``::

    path = "C:\\Your\\Path\\Here\\"
    name = "Dev" # makes filename Dev.son

and create an instance of ``Simulation``. Optionally, you can set a transformation to ``trans`` according `KLayout documentation <https://www.klayout.de/transformations.html>`_ ::

    sim = Simulation(layout, name=name)
    trans = pya.DTrans(0,0) # displacement of 0 and 0
    sim.insert_cell(top_cell, trans=trans, name="Top cell")

Then create an instance of ``SonnetExport``::

    son = SonnetExport(sim, auto_port_detection=True, path=path)

and use the ``write`` command::

    son.write()

All this can be called conveniently from macros/export/export_sonnet.lym

Settings
--------
Settings work as follows when creating an instance of SonnetExport:

    son = SonnetExport(sim, auto_port_detection=False, detailed_resonance=True, path=path)

* **``auto_port_detection`` is required**. True converts all ports in the circuit to Sonnet ports. False converts only manually set annotations (`pya.DText`) containing *sonnet_port*. Use this to limit the Sonnet simulation to, for example, a feedline.

* ``detailed_resonance`` is False as default. More info `here. <https://www.sonnetsoftware.com/support/downloads/techdocs/Enhanced_Resonance_Detection_Feature.pdf>`_

* ``lower_accuracy`` is False as default. False sets Sonnet to Fine/Edge meshing and True to Coarse/Edge Meshing.

* ``fill_type`` is 'Staircase' as default. This sets the default fill type for polygons. The other option is 'Conformal' which can be faster but less accurate. A good workflow could be to set everything to Staircase and then set some meanders to Conformal in Sonnet.

* ``current`` is False as default. True computes currents in Sonnet which adds to simulation time but can used to easily see connection errors.

* ``control`` is 'ABS' as default. Selects what analysis control is used in Sonnet. Options are 'Simple', 'ABS' and 'Sweep' for parameter sweeping.

* ``simulation_safety`` is 0 as default. This adds extra ground area to a simulation environment (in µm).


To improve
-----------

* Add `vias <https://www.sonnetsoftware.com/support/help-17/Sonnet_Suites/..%5Cusers_guide/Sonnet%20User's%20Guide.html?ViaPolygons.html>`_ to connect airbridges to layer underneath
* Automatically identify `calibration groups <https://www.sonnetsoftware.com/support/help-17/Sonnet_Suites/..%5Cusers_guide/Sonnet%20User's%20Guide.html?CalibrationGroupProperties.html>`_ and `push-pull ports <https://www.sonnetsoftware.com/support/help-17/Sonnet_Suites/..%5Cusers_guide/Sonnet%20User's%20Guide.html?PortswithNegativeNumbers.html>`_
