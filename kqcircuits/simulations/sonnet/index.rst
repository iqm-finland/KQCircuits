Exporting to Sonnet
===================
The scope of this script is up to one chip. Generating .son files for wafers can be done but is increasingly slow due to the port-edge finding algorithm. Pre-processing wafers in Sonnet however requires a huge amount of RAM.

Instructions
------------

When you have an active project open, import the following and get the top cell and layout::

    from kqcircuits.klayout_view import KLayoutView
    from kqcircuits.simulations.simulation import Simulation
    from kqcircuits.simulations.sonnet.sonnet_export import SonnetExport

    top_cell = KLayoutView.get_active_cell()
    layout = KLayoutView.get_active_layout()

Set where you want your files. For example, the working directory could be set with ``import os; os.getcwd()``::

    path = "C:\\Users\\Admin\\KLayout\\python\\kqcircuit\\"
    name = "Dev" # makes filename Dev.son

and create an instance of ``Simulation``. Optionally, you can set a transformation to ``trans`` according `KLayout documentation <https://www.klayout.de/transformations.html>`_ ::

    sim = Simulation(layout, name=name)
    trans = pya.DTrans(0,0) # displacement of 0 and 0
    sim.insert_cell(top_cell, trans=trans, name="Top cell")

Then create an instance of ``SonnetExport``::

    son = SonnetExport(sim, path=path)

and use the ``write`` command::

    son.write()

All this can be called conveniently from macros/export/export_sonnet.lym


To improve
-----------

* Add `vias <https://www.sonnetsoftware.com/support/help-17/Sonnet_Suites/..%5Cusers_guide/Sonnet%20User's%20Guide.html?ViaPolygons.html>`_ to connect airbridges to layer underneath
* Automatically identify `calibration groups <https://www.sonnetsoftware.com/support/help-17/Sonnet_Suites/..%5Cusers_guide/Sonnet%20User's%20Guide.html?CalibrationGroupProperties.html>`_ and `push-pull ports <https://www.sonnetsoftware.com/support/help-17/Sonnet_Suites/..%5Cusers_guide/Sonnet%20User's%20Guide.html?PortswithNegativeNumbers.html>`_
