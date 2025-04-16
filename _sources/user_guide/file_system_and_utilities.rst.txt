.. _file_system:

General Structure and Miscellaneous Utilities
=============================================

In the KQCircuits root folder the most important folder for most users is the
:git_url:`klayout_package` folder, which is also all that is included in the Salt
package. Other folders are mainly for automatic tests and documentation.
KQCircuits code is divided into the :git_url:`kqcircuits <klayout_package/python/kqcircuits>`,
:git_url:`scripts <klayout_package/python/scripts>` and :git_url:`requirements <klayout_package/python/requirements>`
folders in :git_url:`klayout_package/python`.
These three folders are also (after installation process) linked as symbolic links ``kqcircuits``,
``kqcircuits_scripts`` and ``kqcircuits_requirements`` in the ``~/.klayout`` or ``~/KLayout`` folder.

The ``kqcircuits`` folder contains all the KQCircuits elements and many
other modules used by them or by scripts. Folders directly under
``kqcircuits`` containing Element classes correspond to different Element
libraries such as elements, chips, or test structures.

The ``scripts`` folder contains macros to be run in KLayout GUI and
scripts for generating simulation files or mask files. Usually, these files are
not meant to be imported in other Python files. The outputs of
simulation or mask scripts can be found in the ``tmp`` folder below the main
KQCircuits folder.

The ``requirements`` folder lists dependent libraries, their versions and their hashes
needed for KQCircuits code.

File system hierarchy
---------------------

High level annotated picture of KQCircuits repository's different subdirectories::

    KQCircuits                      Git repository root
    ├── ci
    ├── docs
    ├── klayout_package
    │   └── python                  Salt package
    │       ├── drc                 Design Rule Checks
    │       ├── kqcircuits          PyPI package
    │       │   ├── chips
    │       │   ├── elements        Basic Elements
    │       │   ├── ...
    │       │   ├── layer_config    Layer visualisation
    │       │   ├── masks           Lithography mask structure
    │       │   ├── simulations     Simulation utilities
    │       │   └── util            Other KQC library functions
    │       └── requirements        Listed dependencies of KQC
    │           ├── linux
    │           ├── mac
    │           └── win
    │       └── scripts
    │           ├── macros
    │           ├── masks
    │           ├── resources
    │           └── simulations
    ├── docs                        Documentation sources
    ├── singularity
    ├── tests                       Pytest files
    │   ├── chips
    │   ├── elements
    │   ├── ...
    ├── util                        Utility scripts

In the KQCircuits root folder the most important folder for most users is the
:git_url:`klayout_package` folder, which is also all that is included in the Salt
package. Other folders are mainly for automatic tests and documentation.
KQCircuits code is divided into the :git_url:`kqcircuits <klayout_package/python/kqcircuits>`,
:git_url:`scripts <klayout_package/python/scripts>` and :git_url:`requirements <klayout_package/python/requirements>`
folders in :git_url:`klayout_package/python`.
These three folders are also (after installation process) linked as symbolic links ``kqcircuits``,
``kqcircuits_scripts`` and ``kqcircuits_requirements`` in the ``~/.klayout`` or ``~/KLayout`` folder.

The ``kqcircuits`` folder contains all the KQCircuits PCell classes and many
other modules used by them or by scripts. Folders directly under
``kqcircuits`` containing PCell classes correspond to different PCell
libraries such as elements, chips, or test structures.

.. note::
   Element classes must be defined in the folder of the corresponding library, and each file should contain exactly
   one element class. The class name in CamelCase should match the file in lower case with underscores.

   KQCircuits automatically registers all elements that adhere to this convention, see
   :git_url:`library_helper.py <klayout_package/python/kqcircuits/util/library_helper.py>` and :git_url:`element.py
   <klayout_package/python/kqcircuits/elements/element.py>`. For more information about the underlying PCell
   libraries see the KLayout documentation pages
   `About Libraries <https://www.klayout.de/doc-qt5/about/about_libraries.html>`_,
   `Class Library <https://www.klayout.de/doc-qt5/code/class_Library.html>`_, and
   `Coding PCells In Ruby <https://www.klayout.de/doc-qt5/programming/ruby_pcells.html#h2-426>`_ (in Ruby).


The ``scripts`` folder contains macros to be run in KLayout GUI and
scripts for generating simulation files or mask files. The files there are in
general not meant to be imported in other Python files. The outputs of
simulation or mask scripts can be found in the ``tmp`` folder below the main
KQCircuits folder.

The ``requirements`` folder lists dependent libraires, their versions and their hashes
needed for KQCircuits code.

Miscellaneous Utilities
-----------------------

The ``util`` folder contains stand alone, self documenting scripts for various practical use cases:

    - ``check_layer_props`` Check or update the layer properties file against values taken from
      KQCircuits' default_layers variable.
    - ``create_element_from_path`` Create a KQCircuits element in KLayout by specifying the path to
      the file containing the element. This script can be used to integrate with external editors.
    - ``gdiff`` Compares a pair of .oas or .gds files or directories containing such files and
      informs you about differences.
    - ``get_klayout_python_info`` is a script designed to be run within KLayout in batch mode,
      and is used to get KLayout information needed by ``setup_within_klayout``.
    - ``netlist_as_graph`` Draw a graph based on a chip's generated netlist file.
    - ``oas2dxf`` Convert .oas to .dxf or the other way around. DXF files are more human readable
      and may be edited with scripts.


Opening :class:`.Element` or :class:`.Chip` from an IDE
-------------------------------------------------------

You can use :git_url:`util/create_element_from_path.py` to open a
:class:`.Element` or :class:`.Chip` in KLayout from your IDE (or just straight from the
command-line).  The script is used as::

    klayout -e -rx -rm util/create_element_from_path.py -rd element_path=kqcircuits/chips/demo.py

And can be easily incorporated as a macro to your IDE.  Check the comments in the function on how to
use it in PyCharm, Visual Studio Code or Vim/NeoVim. The ``element_path`` argument can be given
as a file path that starts from `*Circuits` or `klayout_package/python/`.
The ``element_path`` argument can also be given as an absolute path as long as it has
`*Circuits/klayout_package/python` in the path.
Use what is easiest to implement for your workflow.
