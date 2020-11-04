# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from importlib import import_module
from docutils.parsers.rst import Directive
from docutils import nodes
from pprint import pformat
from sphinx import addnodes

"""
    Sphinx extension for including a Python class member as literal.

    Typical usage example (in .rst file):

    .. literalinclude_member:: kqcircuits.elements.airbridge.Airbridge.PARAMETERS_SCHEMA
"""


class LiteralincludeMemberDirective(Directive):
    """Class for literalinclude_member Sphinx directive.

    This can be used to automatically get the literal representation of a Python class member

    To make this usable in Sphinx documentation, add "literalinclude_member" to conf.py and add this directory to
    sys.path in conf.py.

    """
    required_arguments = 1

    def run(self):
        module_path, class_name, member_name = self.arguments[0].rsplit('.', 2)

        class_data = getattr(import_module(module_path), class_name)
        member_data = getattr(class_data, member_name)

        member_code = pformat(member_data, indent=2)
        literal = nodes.literal_block(member_code, member_code)
        literal["language"] = "python"

        return [addnodes.desc_name(text=member_name), addnodes.desc_content('', literal)]


def setup(app):
    app.add_directive("literalinclude_member", LiteralincludeMemberDirective)