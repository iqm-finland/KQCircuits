Sonnet export
-------------

Once the ``simulation`` object is created, call function ``export_sonnet_son`` to export simulation into ``.son`` file::

    from kqcircuits.simulations.export.sonnet.sonnet_export import export_sonnet_son, export_sonnet
    path = "C:\\Your\\Path\\Here\\"
    son = export_sonnet_son(simulation, path)

Multiple simulations can be exported by calling ``export_sonnet``. The function takes list of simulations as it's first parameter::

    sons = export_sonnet([simulation], path)
