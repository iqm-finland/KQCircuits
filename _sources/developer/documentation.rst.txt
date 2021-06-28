Documentation
-------------

The documentation for KQCircuits is created from the ``.rst`` files in the
``docs`` folder using Sphinx. To build the documentation locally, open the
command line in the ``docs`` folder and write ``make html``. If you want to
completely rebuild the documentation, run ``make clean`` to remove the built
files first.

.. note::
    KLayout needs to be installed for generating PCell images.

The API documentation is generated from the ``.rst`` files in ``docs/api``
folder, which are generated automatically by sphinx-apidoc when you run
``make html``. The template files used to generate these are in
``docs/templates/apidoc``.

There are some custom Sphinx extensions used in the documentation generation,
these are in the ``docs/sphinxext`` folder. Also the
``docs/make_pcell_images.py`` script is used by ``make html`` to create a .png
image of every PCell into the pcell_images directory, these get included in the
API documentation. Image generation may produce harmless error messages in
Windows.
