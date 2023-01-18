Creating simulation object
==========================

Simulation export begins by creating an instance of :class:`.Simulation` class. The simulation object includes following information:

* name (defines export filenames)
* geometry for the simulation
* port locations and types

Geometry from Klayout GUI
^^^^^^^^^^^^^^^^^^^^^^^^^

When you have an active project open, import the following and get the top cell::

    from kqcircuits.klayout_view import KLayoutView
    from kqcircuits.simulations.simulation import Simulation

    top_cell = KLayoutView(current=True).active_cell

Create an instance of :class:`.Simulation`::

    simulation = Simulation.from_cell(top_cell, name='Dev', margin=100)

The ``simulation`` object is needed for Ansys export and Sonnet export (more details in following sections). Alternatively, run following macros in Klayout:

* :git_url:`scripts/macros/export/export_ansys.lym <klayout_package/python/scripts/macros/export/export_ansys.lym>`
* :git_url:`scripts/macros/export/export_sonnet.lym <klayout_package/python/scripts/macros/export/export_sonnet.lym>`

Geometry from KQCircuits library
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Define the geometry and ports in KQCircuits by inheriting :class:`.Simulation` class. Following creates waveguide crossing the domain box::

    from kqcircuits.simulations.simulation import Simulation
    from kqcircuits.pya_resolver import pya
    import sys
    import logging
    from kqcircuits.util.export_helper import get_active_or_new_layout

    class WaveguideSimulation(Simulation):
        def build(self):
            self.produce_waveguide_to_port(pya.DPoint(self.box.left, self.box.center().y),
                                           pya.DPoint(self.box.right, self.box.center().y),
                                           1, 'right', use_internal_ports=False)


Get layout for :class:`.Simulation` object::

    logging.basicConfig(level=logging.WARN, stream=sys.stdout)
    layout = get_active_or_new_layout()

Create an instance of :class:`.Simulation`::

    simulation = WaveguideSimulation(layout, name='Dev', box=pya.DBox(pya.DPoint(0, 0), pya.DPoint(500, 500)))

The :class:`.Simulation` class and it's subclasses are located in folder :git_url:`kqcircuits/simulations/ <klayout_package/python/kqcircuits/simulations>`.
