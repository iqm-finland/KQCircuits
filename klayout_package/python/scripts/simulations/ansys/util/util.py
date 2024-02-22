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


import json


def get_enabled_setup(oDesign, tab="HfssTab"):
    """Returns enabled analysis setup. Returns None if not enabled."""
    setup_names = oDesign.GetModule("AnalysisSetup").GetSetups()
    for name in setup_names:
        if oDesign.GetPropertyValue(tab, "AnalysisSetup:" + name, "Enabled") == "true":
            return name
    return None


def get_enabled_sweep(oDesign, setup, tab="HfssTab"):
    """Returns enabled analysis sweep. Returns None if not enabled."""
    sweep_names = oDesign.GetModule("AnalysisSetup").GetSweeps(str(setup))
    for name in sweep_names:
        if oDesign.GetPropertyValue(tab, "AnalysisSetup:" + setup + ":" + name, "Enabled") == "true":
            return name
    return None


def get_solution_data(report_setup, report_type, solution_name, context_array, families_array, expression):
    """Returns value of given expression. If expression is a list the result is a dictionary."""
    if isinstance(expression, list):
        expressions = expression
    else:
        expressions = [expression]

    # get solution data by frequency and expression
    s = report_setup.GetSolutionDataPerVariation(
        report_type, solution_name, context_array, families_array, expressions
    )[0]

    def getresult(s, expr):
        if s.IsDataComplex(expr):
            return [
                complex(re, im) for (re, im) in zip(s.GetRealDataValues(expr, True), s.GetImagDataValues(expr, True))
            ]
        else:
            return [float(re) for re in s.GetRealDataValues(expr, True)]

    if isinstance(expression, list):
        result = {e: getresult(s, e) for e in expressions}
        result["Freq"] = [float(re) for re in s.GetSweepValues("Freq")]
    else:
        result = getresult(s, expression)

    return result


def get_quantities(report_setup, report_type, solution_name, context_array, category_name):
    """Returns the available quantities in given category"""
    return report_setup.GetAllQuantities(report_type, "Rectangular Plot", solution_name, context_array, category_name)


def create_x_vs_y_plot(
    report_setup,
    plot_name,
    report_type,
    solution_name,
    context_array,
    input_family,
    x_components,
    y_label,
    y_components,
):
    """Create report (plot) with x vs. y in the given context. Report is docked to view."""
    report_setup.CreateReport(
        plot_name,
        report_type,
        "Rectangular Plot",
        solution_name,
        context_array,
        input_family,
        ["X Component:=", x_components, "Y Component:=", y_components],
    )
    report_setup.ChangeProperty(
        [
            "NAME:AllTabs",
            [
                "NAME:Legend",
                ["NAME:PropServers", "%s:Legend" % plot_name],
                [
                    "NAME:ChangedProps",
                    ["NAME:Show Variation Key", "Value:=", False],
                    ["NAME:Show Solution Name", "Value:=", False],
                    ["NAME:DockMode", "Value:=", "Dock Right"],
                ],
            ],
            [
                "NAME:Axis",
                ["NAME:PropServers", "%s:AxisY1" % plot_name],
                ["NAME:ChangedProps", ["NAME:Specify Name", "Value:=", True], ["NAME:Name", "Value:=", y_label]],
            ],
        ]
    )


# Helper class to encode complex data in json output
class ComplexEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, complex):
            return [o.real, o.imag]
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, o)
