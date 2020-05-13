import os
import re
import types
import inspect
import importlib
from pathlib import Path
from autologging import logged, traced

from kqcircuits.pya_resolver import pya

"""
    Helper module for building KLayout libraries.

    Typical usage example:

    from kqcircuits.elements import Element, Airbridge
    from kqcircuits.util.library_helper import load_library
    load_library(Element.LIBRARY_NAME)
    cell = Airbridge.create_cell(layout, {})
"""

LIBRARY_NAMES = {
    "Element": "Element Library",
    "Chip": "Chip Library",
    "TestStructure": "Test Structure Library"
}


@traced
def load_all_libraries(flush=False):
    """Load all KQCircuits libraries.
    """
    libraries = []
    for value in LIBRARY_NAMES.values():
        libraries.append(load_library(value, flush))
    return libraries


@traced
def load_library(name=None, flush=False):
    """Load KQCircuits library.

    If library is not already registered,
    then create and register KQCircuits library.

    Returns:
        A KLayout library populated with all KQCircuits pcells with LIBRARY_NAME=name.
    """
    library = pya.Library.library_by_name(name)
    if library is None:
        return _create_library(name)
    else:
        if flush:
            delete_library(name)
            return _create_library(name, reload=True)
        else:
            return library


@traced
def delete_all_libraries():
    """Delete all KQCircuits libraries from KLayout memory.
    """
    for value in LIBRARY_NAMES.values():
        delete_library(value)


@logged
@traced
def delete_library(name=None):
    """Delete KQCircuits library.
    """
    library = pya.Library.library_by_name(name)
    if library is not None:
        library.delete()
        if library._destroyed():
            delete_library._log.info("Successfully deleted library '{}'.".format(name))
        else:
            raise SystemError("Failed to delete library '[]'.".format(name))


@logged
@traced
def to_module_name(class_name=None):
    """Converts class name to module name.

    Converts PascalCase class name to module name
    with each word lowercase and separated by space.

    Args:
        class_name: Class name.

    Returns:
        A lowercase and spaced by word string.
        For example:

        > module_name = _to_module_name("XMonsDirectCoupling")
        > print(module_name)
        "chip_q_factor"
    """
    try:
        _is_valid_class_name(class_name)
    except ValueError as e:
        to_module_name._log.exception("Failed to convert class name to module name.")
        raise e
    words = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).split("_")
    return _join_module_words(words)


@logged
@traced
def to_library_name(class_name=None):
    """Converts class name to library name.

    Converts PascalCase class name to library name
    with each word titled and separated by space.
    Single letter words are attached to the following word.

    Args:
        class_name: Class name.

    Returns:
        A titled and spaced by word string which may be used as library name.
        For example:

        > library_name = to_library_name("XMonsDirectCoupling")
        > print(library_name)
        "XMons Direct Coupling"
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
@traced
def _create_library(name=None, reload=False):
    """Create KQCircuits library.

    Create KLayout library containing KQCircuits examples.

    Returns:
        A KLayout library populated with all available KQCircuits examples.
    """
    if name is None:
        msg = "Missing library name."
        error = ValueError(msg)
        _create_library._log.error(msg)
        raise error
    library = pya.Library()
    kqcircuits_path = Path(os.path.dirname(os.path.abspath(__file__))).parent
    module_paths = kqcircuits_path.rglob("*.py")
    for path in module_paths:
        module_name = path.stem
        if module_name == "__init__":
            continue
        try:
            # Get the module path starting from the "kqcircuits" directory below project root directory,
            # assuming that there is exactly one directory named "kqcircuits" below the project root.
            import_path_parts = path.parts[::-1][path.parts[::-1].index("kqcircuits")::-1]
            import_path = ".".join(import_path_parts)[:-3]  # the -3 is for removing ".py" from the path

            module = importlib.import_module(import_path)
            if reload:
                importlib.reload(module)
                _create_library._log.debug("Reloaded module '{}'.".format(module_name))
            class_list = _get_classes(module)
            for cls in class_list:
                _create_library._log.info("Comparing name {} to cls.LIBRARY_NAME {}.".format(name, cls.LIBRARY_NAME))
                if name == cls.LIBRARY_NAME:
                    if not library.description:
                        library.description = cls.LIBRARY_DESCRIPTION
                    library_name = to_library_name(cls.__name__)
                    library.layout().register_pcell(library_name, cls())
                    _create_library._log.debug("Registered pcell [{}] to library {}.".format(library_name, name))
        except Exception as e:
            _create_library._log.warning(
                "Failed to register pcell in module {} to library {}.".format(module_name, name),
                exc_info=True
            )
            pass
    if name == LIBRARY_NAMES["Element"]:
        shape_paths = kqcircuits_path.rglob("*.oas")
        for path in shape_paths:
            library.layout().read(str(path.absolute()))
    if len(library.layout().pcell_names()) > 0:
        library.register(name)
        _create_library._log.info("Created library {}.".format(name))
        return library
    else:
        return None


@traced
def _get_classes(module=None):
    """Returns all classes found for specified path and circuit type.

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
        Array of module paths.
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


@logged
@traced
def _is_valid_class_name(value=None):
    """Check if string value is valid PEP-8 compliant Python class name.
    """
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


@logged
@traced
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
