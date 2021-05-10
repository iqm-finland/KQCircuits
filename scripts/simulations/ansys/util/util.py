# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy's prior
# written permission.

import json


def get_enabled_setup(oDesign, tab="General"):
    """Returns enabled analysis setup. Returns None if not enabled."""
    setup_names = oDesign.GetModule("AnalysisSetup").GetSetups()
    for name in setup_names:
        if 'true' == oDesign.GetPropertyValue(tab, "AnalysisSetup:" + name, "Enabled"):
            return name
    return None


def get_enabled_setup_and_sweep(oDesign, tab="HfssTab"):
    """Returns enabled analysis setup and sweep. Returns None if not enabled."""
    setup = get_enabled_setup(oDesign, tab)
    if setup is None:
        return (None, None)

    sweep_names = oDesign.GetModule("AnalysisSetup").GetSweeps(str(setup))
    for name in sweep_names:
        if 'true' == oDesign.GetPropertyValue(tab, "AnalysisSetup:" + setup + ":" + name, "Enabled"):
            return (setup, name)
    return (setup, None)


def get_solution_data(report_setup, report_type, solution_name, context_array, families_array, expression):
    """Returns value of given expression. If expression is a list the result is a dictionary."""
    if isinstance(expression, list):
        expressions = expression
    else:
        expressions = [expression]

    # get solution data by frequency and expression
    s = report_setup.GetSolutionDataPerVariation(report_type, solution_name, context_array, families_array,
                                                 expressions)[0]

    def getresult(s, expr):
        if s.IsDataComplex(expr):
            return ([complex(re, im) for (re, im) in zip(
                s.GetRealDataValues(expr, True),
                s.GetImagDataValues(expr, True))])
        else:
            return [float(re) for re in s.GetRealDataValues(expr, True)]

    if isinstance(expression, list):
        result = {e: getresult(s, e) for e in expressions}
        result['Freq'] = [float(re) for re in s.GetSweepValues('Freq')]
    else:
        result = getresult(s, expression)

    return result


# Helper class to encode complex data in json output
class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, complex):
            return [obj.real, obj.imag]
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)
