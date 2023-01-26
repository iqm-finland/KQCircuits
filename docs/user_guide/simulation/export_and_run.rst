Run and export in one line
==========================

KQC simulations are first exported to a folder and then run as a shell script.
It is convenient to run KQC simulations as a one liner. This can be done
with the :git_url:`export_and_run.py <klayout_package/python/kqcircuits/simulations/export/export_and_run.py>` script.

Go to directory 'klayout_package/python' and run::

    kqc simulate klayout_package/python/scripts/simulations/waveguides_sim_compare.py

or if you do not want the GUI dialogs::
    
    kqc simulate klayout_package/python/scripts/simulations/waveguides_sim_compare.py -q

.. note::
   On Windows you may need to install KQC (``pip install -e .``) with admin priviledges
   (depending on whether Python install is in `Program Files` or `AppData`)
