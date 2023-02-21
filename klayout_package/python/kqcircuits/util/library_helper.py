# This code is part of KQCircuits
# Copyright (C) 2021 IQM Finland Oy
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not, see
# https://www.gnu.org/licenses/gpl-3.0.html.
#
# The software distribution should follow IQM trademark policy for open-source software
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).

"""
    Helper module for building KLayout libraries.

    Typical usage example::

        from kqcircuits.elements.airbridges import Airbridge
        from kqcircuits.util.library_helper import load_libraries
        load_libraries(path=Airbridge.LIBRARY_PATH)
        cell = Airbridge.create(layout, **kwargs)
"""

import os
import re
import types
import inspect
import importlib
from pathlib import Path
from autologging import logged

from kqcircuits.defaults import SRC_PATHS, kqc_library_names
from kqcircuits.pya_resolver import pya


_kqc_libraries = {}  # dictionary {library name: (library, library path relative to kqcircuits)}

# Source directories not to be included in the library
_excluded_paths = (
    "__pycache__",
    "util",
    "simulations",
    "masks",
    "layer_config",
)

# modules NOT to be included in the library, (python file names without extension)
_excluded_module_names = (
    "__init__",
    "element",
    "qubit",
    "airbridge",
    "test_structure",
    "flip_chip_connector",
    "junction",
    "squid",
    "fluxline",
    "marker",
    "junction_test_pads",
    "tsv",
)

# Add user directories to SRC_PATHS when using Salt package.
if SRC_PATHS[0].parts[-4] == "salt":
    user_dirs = os.path.join(SRC_PATHS[0].parents[3], "python")
    for ud in os.listdir(user_dirs):
        SRC_PATHS.append(Path(os.path.join(user_dirs, ud)))


@logged
def load_libraries(flush=False, path=""):
    """Load all KQCircuits libraries from the given path.

    Args:
        flush: If True, old libraries will be deleted and new ones created. Otherwise old libraries will be used.
            (if old libraries exist)
        path: path (relative to SRC_PATH) from which the pcell classes and cells are loaded to libraries

    Returns:
         A dictionary of libraries that have been loaded, keys are library names and values are libraries.
    """

    if flush:
        delete_all_libraries()
        _kqc_libraries.clear()
        load_libraries._log.debug("Deleted all libraries.")
    else:
        # if a library with the given path already exist, use it
        for _, lib_path in _kqc_libraries.values():
            if lib_path == path:
                return {key: value[0] for key, value in _kqc_libraries.items()}

    for cls in _get_all_pcell_classes(flush, path):

        library_name = cls.LIBRARY_NAME
        library_path = cls.LIBRARY_PATH

        library = pya.Library.library_by_name(library_name)  # returns only registered libraries
        if (library is None) or flush:
            if library_name in _kqc_libraries.keys():
                load_libraries._log.debug("Using created library \"{}\".".format(library_name))
                library, _ = _kqc_libraries[library_name]
            else:
                # create a library, but do not register it yet
                load_libraries._log.debug("Creating new library \"{}\".".format(library_name))
                library = pya.Library()
                library.description = cls.LIBRARY_DESCRIPTION
                _kqc_libraries[library_name] = (library, library_path)
            _register_pcell(cls, library, library_name)

    # Libraries should be registered in dependency-order, otherwise reload will crash.
    for library_name in kqc_library_names:
        if library_name not in _kqc_libraries:
            continue
        library, _ = _kqc_libraries[library_name]
        _load_manual_designs(library_name)
        if library_name not in library.library_names():
            library.register(library_name)  # library must be registered only after all cells have been added to it

    return {key: value[0] for key, value in _kqc_libraries.items()}


def get_library_paths():
    """Returns a list of library paths under kqcircuits."""
    return (path for _, path in _kqc_libraries.values())


def delete_all_libraries():
    """Delete all KQCircuits libraries from KLayout memory."""
    for name in reversed(kqc_library_names):
        delete_library(name)


@logged
def delete_library(name=None):
    """Delete a KQCircuits library.

    Calls library.delete() and removes the library from _kqc_libraries dict. Also deletes any libraries which have this
    library as a dependency.

    Args:
        name: name of the library
    """
    if name is None:
        return
    library = pya.Library.library_by_name(name)
    if library is None:  # already deleted
        return

    # delete this library
    library.delete()
    if name in _kqc_libraries:
        _kqc_libraries.pop(name)
    if library._destroyed():
        delete_library._log.info("Successfully deleted library '{}'.".format(name))
    else:
        raise SystemError("Failed to delete library '[]'.".format(name))


def element_by_class_name(class_name: str, library_path: str = "elements", library_name: str = "Element Library"):
    """
    Find Element class by class name from a library

    Args:
        class_name: Class name to look up
        library_path: Path to pass to load_libraries
        library_name: Name of the library

    Returns: Class of the element, or None if the element is not in the library
    """
    layout = load_libraries(path=library_path)[library_name].layout()
    for pcell_id in layout.pcell_ids():
        pcell_class = layout.pcell_declaration(pcell_id).__class__
        if pcell_class.__name__ == class_name:
            return pcell_class

    return None


@logged
def to_module_name(class_name=None):
    """Converts class name to module name.

    Converts PascalCase class name to module name
    with each word lowercase and separated by space.

    Args:
        class_name: Class name.

    Returns:
        A lowercase and spaced by word string.

        For example::
            > module_name = _to_module_name("QualityFactor")
            > print(module_name)
            "quality_factor"
    """
    try:
        _is_valid_class_name(class_name)
    except ValueError as e:
        to_module_name._log.exception("Failed to convert class name to module name.")
        raise e
    words = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).split("_")
    return _join_module_words(words)


@logged
def to_library_name(class_name=None):
    """Converts class name to library name.

    Converts PascalCase class name to library name
    with each word titled and separated by space.
    Single letter words are attached to the following word.

    Args:
        class_name: Class name.

    Returns:
        A titled and spaced by word string which may be used as library name.

        For example::
            > library_name = to_library_name("QualityFactor")
            > print(library_name)
            "Quality Factor"
    """
    try:
        _is_valid_class_name(class_name)
    except ValueError as e:
        to_library_name._log.exception("Failed to convert class name to library name.")
        raise e
    words = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).split("_")
    return _join_library_words(words)


# ********************************************************************************
# PRIVATE METHODS
# ********************************************************************************


@logged
def _register_pcell(pcell_class, library, library_name):
    """Registers the PCell to the library.

    Args:
        pcell_class: class of the PCell
        library: Library where the PCell is registered to
        library_name: name of the library
    """
    try:
        pcell_name = to_library_name(pcell_class.__name__)
        library.layout().register_pcell(pcell_name, pcell_class())
        _register_pcell._log.debug("Registered pcell [{}] to library {}.".format(pcell_name, library_name))
    except Exception:  # pylint: disable=broad-except
        _register_pcell._log.warning(
            "Failed to register pcell in class {} to library {}.".format(pcell_class, library_name),
            exc_info=True
        )


def _load_manual_designs(library_name):
    """Loads .oas files to the library

    Args:
        library_name: name of the library
    """
    library, rel_path = _kqc_libraries[library_name]

    for src in SRC_PATHS:
        for path in src.rglob("{}/**/*.oas".format(rel_path)):
            library.layout().read(str(path.absolute()))


@logged
def _get_all_pcell_classes(reload=False, path=""):
    """Returns all PCell classes in the given path.

    Args:
        reload: Boolean determining if the modules in kqcircuits should be reloaded.
        path: path (relative to SRC_PATH) from which the classes are searched

    Returns:
        List of the PCell classes
    """
    pcell_classes = []

    for src in SRC_PATHS:
        pkg = src.parts[-1]

        if path == "":
            library_src_paths = [f for f in src.iterdir() if f.is_dir() and f.name not in _excluded_paths]
        else:
            library_src_paths = [src.joinpath(path)]

        for library_src in library_src_paths:
            module_paths = library_src.rglob("*.py")
            for mp in module_paths:
                module_name = mp.stem
                if module_name in _excluded_module_names:
                    continue
                # Get the module path starting from the "pkg" directory below project root directory.
                import_path_parts = mp.parts[::-1][mp.parts[::-1].index(pkg)::-1]
                import_path = ".".join(import_path_parts)[:-3]  # the -3 is for removing ".py" from the path

                module = importlib.import_module(import_path)
                if reload:
                    importlib.reload(module)
                    _get_all_pcell_classes._log.debug("Reloaded module '{}'.".format(module_name))

                classes = _get_pcell_classes(module)
                if classes:
                    pcell_classes.append(classes[-1])

    return pcell_classes


def _get_pcell_classes(module=None):
    """Returns all PCell classes found in the module.

    Args:
        module: Module.

    Returns:
        Array of classes.
    """
    if module is None:
        return []
    class_list = []
    for member in inspect.getmembers(module, inspect.isclass):
        if member[1].__module__ == module.__name__:
            cls = _get_pcell_class(member[0], module)
            if cls is not None:
                class_list.append(cls)
    return class_list


def _get_pcell_class(name=None, module=None):
    """Returns class found for specified path and circuit type.

    Args:
        name: Path object for module.
        module: Module.

    Returns:
        The class if it is subclass of PCellDeclarationHelper, otherwise None.
    """
    if name is None or not isinstance(name, str):
        return None
    if module is None or not isinstance(module, types.ModuleType):
        return None
    value = getattr(module, name)
    if isinstance(value, type) and issubclass(value, pya.PCellDeclarationHelper):
        return value
    else:
        return None

def _is_valid_class_name(value=None):
    """Check if string value is valid PEP-8 compliant Python class name."""
    if value is None or not isinstance(value, str) or len(value) == 0:
        raise ValueError("Cannot convert nil or non-string class name '{}' to library name.".format(value))
    if re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", value) is None:
        raise ValueError("Cannot convert invalid Python class name '{}' to library name.".format(value))
    if re.fullmatch(r"([A-Z][a-z0-9]*)+", value) is None:
        raise ValueError("PEP8 compliant class name '{}' must be PascalCase without underscores.".format(value))


def _join_module_words(words=None):
    """Join words to build module name.

    Joins words such that each word is lowercase and separated by underscore.
    Single letter words are attached to the following word.

    Args:
        words: List of word strings

    Returns:
        A string which may be used as module name.
    """
    words = _clean_words(words)
    words = [w.lower() for w in words]
    n = len(words)
    if n == 0:
        return ""
    name = words[0]
    for i in range(1, n):
        previous = words[i - 1]
        current = words[i]
        if len(previous) == 1:
            name += current
        else:
            name += "_" + current
    return name


def _join_library_words(words=None):
    """Join words to build library name.

    Joins words such that each word is titled and separated by space.
    Single letter words are attached to the following word.

    Args:
        words: List of word strings

    Returns:
        A string which may be used as library name.
    """
    words = _clean_words(words)
    n = len(words)
    if n == 0:
        return ""
    name = words[0].title()
    for i in range(1, n):
        previous = words[i - 1].title()
        current = words[i].title()
        if len(previous) == 1:
            name += current
        else:
            name += " " + current
    return name


@logged
def _clean_words(words=None):
    """Clean word list by removing None values, empty strings, and non-string values.

    Returns:
        Clean word list.
    """
    if words and isinstance(words, list):
        words = list(filter(None, words))
        words = list(filter(lambda item: isinstance(item, str), words))
        return list(filter(len, words))
    else:
        return []
