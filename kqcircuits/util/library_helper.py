# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import re
import types
import inspect
import importlib
from autologging import logged, traced

from kqcircuits.defaults import SRC_PATH
from kqcircuits.pya_resolver import pya

"""
    Helper module for building KLayout libraries.

    Typical usage example:

    from kqcircuits.elements import Airbridge
    from kqcircuits.util.library_helper import load_libraries
    load_libraries(path=Airbridge.LIBRARY_PATH)
    cell = Airbridge.create(layout, **kwargs)
"""

_kqc_libraries = {}  # dictionary {library name: (library, library path relative to kqcircuits)}

# modules NOT to be included in the library, (python file names without extension)
_excluded_module_names = (
    "__init__", "library_helper",
    "element",
    "qubit",
    "test_structure",
    "flip_chip_connector",
)

@traced
@logged
def load_libraries(flush=False, path=""):
    """Load all KQCircuits libraries from the given path.

    Args:
        flush: If True, old libraries will be deleted and new ones created. Otherwise old libraries will be used.
            (if old libraries exist)
        path: path (relative to SRC_PATH) from which the pcell classes and cells are loaded to libraries

    Returns:
         A list of libraries that have been loaded.
    """

    if flush:
        delete_all_libraries()
        _kqc_libraries.clear()
        load_libraries._log.debug("Deleted all libraries.")
    else:
        # if a library with the given path already exist, use it
        for lib, lib_path in _kqc_libraries.values():
            if lib_path == path:
                return [value[0] for value in _kqc_libraries.values()]

    pcell_classes = _get_all_pcell_classes(flush, path)

    for cls in pcell_classes:

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

    for library_name, (library, _) in _kqc_libraries.items():
        _load_manual_designs(library_name)
        if library_name not in library.library_names():
            library.register(library_name)  # library must be registered only after all cells have been added to it

    return [value[0] for value in _kqc_libraries.values()]


@traced
def delete_all_libraries():
    """Delete all KQCircuits libraries from KLayout memory."""
    for name in list(_kqc_libraries.keys()):
        delete_library(name)


@traced
@logged
def delete_library(name=None):
    """Delete a KQCircuits library.

    Calls library.delete() and removes the library from _kqc_libraries dict.

    Args:
        name: name of the library
    """
    library = pya.Library.library_by_name(name)
    if library is not None:
        library.delete()
        if name in _kqc_libraries:
            _kqc_libraries.pop(name)
        if library._destroyed():
            delete_library._log.info("Successfully deleted library '{}'.".format(name))
        else:
            raise SystemError("Failed to delete library '[]'.".format(name))


@traced
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


@traced
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


@traced
@logged
def _register_pcell(pcell_class, library, library_name):
    """Registers the PCell to the libary.

    Args:
        pcell_class: class of the PCell
        library: Library where the PCell is registered to
        library_name: name of the library
    """
    try:
        pcell_name = to_library_name(pcell_class.__name__)
        library.layout().register_pcell(pcell_name, pcell_class())
        _register_pcell._log.debug("Registered pcell [{}] to library {}.".format(pcell_name, library_name))
    except Exception as e:
        _register_pcell._log.warning(
            "Failed to register pcell in class {} to library {}.".format(pcell_class, library_name),
            exc_info=True
        )


@traced
def _load_manual_designs(library_name):
    """Loads .oas files to the library

    Args:
        library_name: name of the library
    """
    library, rel_path = _kqc_libraries[library_name]
    shape_paths = SRC_PATH.rglob("{}/*.oas".format(rel_path))
    for path in shape_paths:
        library.layout().read(str(path.absolute()))


@traced
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
    module_paths = SRC_PATH.joinpath(path).rglob("*.py")

    for path in module_paths:
        module_name = path.stem
        if module_name in _excluded_module_names:
            continue
        # Get the module path starting from the "kqcircuits" directory below project root directory,
        # assuming that there is exactly one directory named "kqcircuits" below the project root.
        import_path_parts = path.parts[::-1][path.parts[::-1].index("kqcircuits")::-1]
        import_path = ".".join(import_path_parts)[:-3]  # the -3 is for removing ".py" from the path

        module = importlib.import_module(import_path)
        if reload:
            importlib.reload(module)
            _get_all_pcell_classes._log.debug("Reloaded module '{}'.".format(module_name))
        pcell_classes += _get_pcell_classes(module)

    return pcell_classes


@traced
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


@traced
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


@traced
def _is_valid_class_name(value=None):
    """Check if string value is valid PEP-8 compliant Python class name."""
    if value is None or not isinstance(value, str) or len(value) == 0:
        raise ValueError("Cannot convert nil or non-string class name '{}' to library name.".format(value))
    if re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", value) is None:
        raise ValueError("Cannot convert invalid Python class name '{}' to library name.".format(value))
    if re.fullmatch(r"([A-Z][a-z0-9]*)+", value) is None:
        raise ValueError("PEP8 compliant class name '{}' must be PascalCase without underscores.".format(value))


@traced
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


@traced
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


@traced
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
