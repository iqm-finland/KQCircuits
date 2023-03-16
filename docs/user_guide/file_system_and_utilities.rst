General Structure and Miscellaneous Utilities
=============================================

File system hierarchy
---------------------

High level annotated picture of KQCircuits repository's different subdirectories::

    KQCircuits                      Git repository root
    ├── ci
    ├── klayout_package
    │   └── python                  Salt package
    │       ├── console_scripts
    │       ├── drc                 Design Rule Checks
    │       ├── kqcircuits          PyPI package
    │       │   ├── chips
    │       │   ├── elements        Basic Elements
    │       │   └── ...
    │       └── scripts
    │           ├── macros
    │           ├── masks
    │           └── simulations
    ├── docs                        Documentation sources
    ├── singularity
    ├── tests                       Pytest files
    │   ├── chips
    │   ├── elements
    │   ├── ...
    ├── util                        Utility scripts
    └── xsection

In the KQCircuits root folder the most important folder for most users is the
:git_url:`klayout_package` folder, which is also all that is included in the Salt
package. Other folders are mainly for automatic tests and documentation.
KQCircuits code is divided into the :git_url:`kqcircuits <klayout_package/python/kqcircuits>` and
:git_url:`scripts <klayout_package/python/scripts>` folders in :git_url:`klayout_package/python`.
These two folders are also (after installation process) linked as symbolic links ``kqcircuits`` and
``kqcircuits_scripts`` in the ``~/.klayout`` or ``~/KLayout`` folder.

The ``kqcircuits`` folder contains all the KQCircuits PCell classes and many
other modules used by them or by scripts. Folders directly under
``kqcircuits`` containing PCell classes correspond to different PCell
libraries such as elements, chips, or test structures.

The ``scripts`` folder contains macros to be run in KLayout GUI and
scripts for generating simulation files or mask files. The files there are in
general not meant to be imported in other Python files. The outputs of
simulation or mask scripts can be found in the ``tmp`` folder below the main
KQCircuits folder.


Miscellaneous Utilities
-----------------------

The ``util`` folder contains stand alone, self documenting scripts for various practical use cases:

    - ``check_layer_props`` Check or update the layer properties file against values taken from
      KQCircuit's default_layers variable.
    - ``create_element_from_path`` Create a KQCircuits element in KLayout by specifying the path to
      the file containing the element. This script can be used to integrate with external editors.
    - ``gdiff`` Compares a pair of .oas or .gds files or directories containing such files and
      informs you about differences.
    - ``netlist_as_graph`` Draw a graph based on a chip's generated netlist file.
    - ``oas2dxf`` Convert .oas to .dxf or the other way around. DXF files are more human readable
      and may be edited with scripts.
