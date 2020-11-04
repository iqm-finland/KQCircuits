# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy's prior
# written permission.

import json


def get_solution_data(oReportSetup, expression, freq=None):
    if freq is None:
        fstring = ["All"]
    elif isinstance(freq, list):
        fstring = [str(f) for f in freq]
    else:
        fstring = [str(freq)]

    if isinstance(expression, list):
        expressions = expression
    else:
        expressions = [expression]

    s = oReportSetup.GetSolutionDataPerVariation(
        "Terminal Solution Data",
        "Setup1 : Sweep",
        ["Domain:=", "Sweep"],
        ["Freq:=", fstring],
        expressions)[0]

    def getresult(s, expression):
        if s.IsDataComplex(expression):
            return ([complex(re, im) for (re, im) in zip(
                s.GetRealDataValues(expression, True),
                s.GetImagDataValues(expression, True))])
        else:
            return ([float(re) for re in s.GetRealDataValues(expression, True)])

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
