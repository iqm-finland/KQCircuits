Documentation
-------------

The documentation for KQCircuits is created from the ``.rst`` files in the
``docs`` folder using Sphinx. To build the documentation locally, open the
command line in the ``docs`` folder and write ``make html``. If you want to
completely rebuild the documentation, run ``make clean`` to remove the built
files first.

The API documentation is generated from the ``.rst`` files in ``docs/api``
folder, which are generated automatically by sphinx-apidoc when you run
``make html``. The template files used to generate these are in
:git_url:`docs/templates/apidoc`.

There are some custom Sphinx extensions used in the documentation generation,
these are in the :git_url:`docs/sphinxext` folder. Also the
:git_url:`docs/make_pcell_images.py` script is used by ``make html`` to create a .png
image of every PCell into the pcell_images directory, these get included in the
API documentation.

The docstring of PCell classes may contain a ``.. MARKERS_FOR_PNG x,y x_2,y_2, ...`` line that will
annotate the generated .png image with "rulers" documenting the important dimensions of the design.
The rulers are placed according to KLayout's rules for rulers going through a specified point.
These annotations should preferably also have the name of the parameter controlling the illustrated
dimensions, like ``.. MARKERS_FOR_PNG x,y,param_name``. Some times KLayout's automatic ruler
placement is not satisfactory in this case the user may specify both starting and ending points of
the ruler ``.. MARKERS_FOR_PNG x,y,x2,y2[,param_name]``.
