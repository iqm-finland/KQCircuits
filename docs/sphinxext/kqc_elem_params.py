# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from importlib import import_module
from docutils.parsers.rst import Directive
from docutils import nodes
import inspect

from kqcircuits.pya_resolver import pya

"""
    Sphinx extension for formatting the PARAMETERS_SCHEMA of KQC elements.

    Typical usage example (in .rst file):

    .. kqc_elem_params:: kqcircuits.elements.airbridge
"""

pcell_parameter_types = {
    pya.PCellParameterDeclaration.TypeBoolean: "Boolean",
    pya.PCellParameterDeclaration.TypeDouble: "Double",
    pya.PCellParameterDeclaration.TypeInt: "Int",
    pya.PCellParameterDeclaration.TypeLayer: "Layer",
    pya.PCellParameterDeclaration.TypeList: "List",
    pya.PCellParameterDeclaration.TypeNone: "None",
    pya.PCellParameterDeclaration.TypeShape: "Shape",
    pya.PCellParameterDeclaration.TypeString: "String",
}


class KqcElemParamsDirective(Directive):
    """Class for kqc_elem_params Sphinx directive.

    This can be used to automatically create descriptions of a KQCircuits element's pcell parameters
    (defined in the PARAMETERS_SCHEMA) for Sphinx documentation.

    To make this usable in Sphinx documentation, add "kqc_elem_params" to conf.py and add this directory to
    sys.path in conf.py.

    """
    required_arguments = 1

    def run(self):
        module_path = self.arguments[0]
        module = import_module(module_path)

        found_parameters_schema = False
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                cls = obj
                if cls.__module__ == module.__name__:
                    for name2, obj2 in inspect.getmembers(cls):
                        if name2 == "PARAMETERS_SCHEMA":
                            parameters_schema = obj2
                            found_parameters_schema = True
                            break
                    if found_parameters_schema:
                        break

        if found_parameters_schema:

            parameters_list = nodes.bullet_list("")

            for key in parameters_schema:
                parameter_paragraph = nodes.paragraph()
                parameter_paragraph += nodes.strong("", key)
                parameter_paragraph += nodes.emphasis("", " (" + pcell_parameter_types[parameters_schema[key]["type"]]
                                                      + ")")
                if "docstring" in parameters_schema[key]:
                    parameter_paragraph += nodes.inline("", " - " + parameters_schema[key]["docstring"])
                else:
                    parameter_paragraph += nodes.inline("", " - " + parameters_schema[key]["description"])
                if "default" in parameters_schema[key]:
                    parameter_paragraph += nodes.emphasis("", ", default=")
                    parameter_paragraph += nodes.literal("", str(parameters_schema[key]["default"]))
                if "choices" in parameters_schema[key]:
                    parameter_paragraph += nodes.emphasis("", ", choices=")
                    choices_list = [choice[1] for choice in parameters_schema[key]["choices"]]
                    parameter_paragraph += nodes.literal("", str(choices_list))
                parameters_list += nodes.list_item("", parameter_paragraph)

            return [nodes.strong("", "PCell parameters:"), nodes.line("", ""), parameters_list]

        else:
            return []


def setup(app):
    app.add_directive("kqc_elem_params", KqcElemParamsDirective)
