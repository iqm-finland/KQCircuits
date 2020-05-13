from importlib import import_module
from docutils.parsers.rst import Directive
from docutils import nodes

"""
    Sphinx extension for formatting the PARAMETERS_SCHEMA of KQC elements.

    Typical usage example (in .rst file):

    .. kqc_elem_params:: kqcircuits.elements.airbridge.Airbridge.PARAMETERS_SCHEMA
"""


class KqcElemParamsDirective(Directive):
    """Class for kqc_elem_params Sphinx directive.

    This can be used to automatically create descriptions of a KQCircuits Element's parameters
    in the PARAMETERS_SCHEMA for Sphinx documentation.

    To make this usable in Sphinx documentation, add "kqc_elem_params" to conf.py and add this directory to
    sys.path in conf.py.

    """
    required_arguments = 1

    def run(self):
        module_path, class_name, member_name = self.arguments[0].rsplit('.', 2)

        class_data = getattr(import_module(module_path), class_name)
        parameters_schema = getattr(class_data, member_name)

        parameters_list = nodes.bullet_list("")

        for key in parameters_schema:
            parameter_paragraph = nodes.paragraph()
            parameter_paragraph += nodes.literal("", key)
            parameter_paragraph += nodes.inline("", " - " + parameters_schema[key]["description"])
            parameters_list += nodes.list_item("", parameter_paragraph)

        return [nodes.strong("", "Parameters:"), nodes.line("", ""), parameters_list]


def setup(app):
    app.add_directive("kqc_elem_params", KqcElemParamsDirective)
