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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


from importlib import import_module
from docutils.parsers.rst import Directive
from docutils import nodes
import inspect
import os
from shutil import copyfile

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt

"""
    Sphinx extension for formatting the parameters of KQC elements.

    Typical usage example (in .rst file):

    .. kqc_elem_params:: kqcircuits.elements.airbridges.airbridge
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
    (defined as Param objects) for Sphinx documentation.

    To make this usable in Sphinx documentation, add "kqc_elem_params" to conf.py and add this directory to
    sys.path in conf.py.

    """

    required_arguments = 1

    def run(self):
        module_path = self.arguments[0]
        module = import_module(module_path)

        targetpng = f"pcell_images/{module.__name__}.png"
        if not os.path.isfile(targetpng):
            copyfile("images/empty.png", targetpng)

        found_parameters_schema = False
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                cls = obj
                if cls.__module__ == module.__name__:
                    if hasattr(cls, "get_schema"):
                        parameters_schema = cls.get_schema(noparents=True)
                        if parameters_schema:
                            found_parameters_schema = True
                    if found_parameters_schema:
                        break

        if found_parameters_schema:

            parameters_list = nodes.bullet_list("")

            for key in parameters_schema:
                param = parameters_schema[key]

                parameter_paragraph = nodes.paragraph()
                parameter_paragraph += nodes.strong("", key)
                parameter_paragraph += nodes.emphasis("", " (" + pcell_parameter_types[param.data_type] + ")")
                if "docstring" in param.kwargs.keys():
                    parameter_paragraph += nodes.inline("", " - " + param.kwargs["docstring"])
                else:
                    parameter_paragraph += nodes.inline("", " - " + param.description)
                parameter_paragraph += nodes.emphasis("", ", default=")
                parameter_paragraph += nodes.literal("", str(param.default))

                if "unit" in param.kwargs.keys():
                    parameter_paragraph += nodes.emphasis("", ", unit=")
                    parameter_paragraph += nodes.literal("", param.kwargs["unit"])
                if "choices" in param.kwargs.keys():
                    parameter_paragraph += nodes.emphasis("", ", choices=")
                    choices_list = [
                        choice if isinstance(choice, str) else choice[1] for choice in param.kwargs["choices"]
                    ]
                    parameter_paragraph += nodes.literal("", str(choices_list))

                parameters_list += nodes.list_item("", parameter_paragraph)

            return [nodes.strong("", "PCell parameters:"), nodes.line("", ""), parameters_list]

        else:
            return []


def setup(app):
    app.add_directive("kqc_elem_params", KqcElemParamsDirective)
