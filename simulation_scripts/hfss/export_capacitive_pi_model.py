# This is a Python 2.7 script that should be run in HFSS in order to import and run the simulation
import time
import os
import sys
import json
import ScriptEnv
# TODO: Figure out how to set the python path for the HFSS internal IronPython
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'util'))
from util import get_solution_data, ComplexEncoder

## SET UP ENVIRONMENT
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.AddMessage("", "", 0, "Exporting PI model results (%s)" % time.asctime(time.localtime()))

fref = 1e9

oDesktop.RestoreWindow()
oProject = oDesktop.GetActiveProject()
oDesign = oProject.GetActiveDesign()
oBoundarySetup = oDesign.GetModule("BoundarySetup")
oOutputVariable = oDesign.GetModule("OutputVariable")
oReportSetup = oDesign.GetModule("ReportSetup")

path = oProject.GetPath()
basename = oProject.GetName()
ports = oBoundarySetup.GetExcitations()[::2]

yyMatrix = [[get_solution_data(oReportSetup, "yy_%s_%s" % (port_i, port_j), fref)[0] for port_j in ports] for port_i in
            ports]
CMatrix = [[get_solution_data(oReportSetup, "C_%s_%s" % (port_i, port_j), fref)[0] for port_j in ports] for port_i in
           ports]

# Calculate total capacitance to ground for each port
Cg = []
for i in range(len(ports)):
    Cg.append(CMatrix[i][i] + sum([1/(1/CMatrix[i][j]+1/CMatrix[j][j]) for j in range(len(ports)) if i != j]))

print('\n'.join([' '.join(['%8.3f' % (item * 1e15) for item in row]) for row in CMatrix]))

# Save CMatrix in readable format
outfile = open(os.path.join(path, basename + '_CMatrix.txt'), 'w')
outfile.write("CMatrix at %.1f GHz:\n" % (fref / 1e9) + '\n'.join(
    ['\t'.join(['%8.3f' % (item * 1e15) for item in row]) for row in CMatrix]) + '\n')
outfile.write("Total C to ground at %.1f GHz:\n" % (fref / 1e9) +
    '\t'.join(['%8.3f' % (item * 1e15) for item in Cg]) + '\n')
outfile.close()

# Save results in json format
outfile = open(os.path.join(path, basename + '_results.json'), 'w')
json.dump(
    {
        'CMatrix': CMatrix,
        'Cg': Cg,
        'yyMatrix': yyMatrix,
        'fref': fref,
        'yydata': get_solution_data(oReportSetup,
                                   ["yy_%s_%s" % (port_i, port_j) for port_j in ports for port_i in ports]),
        'Cdata': get_solution_data(oReportSetup,
                                   ["C_%s_%s" % (port_i, port_j) for port_j in ports for port_i in ports])
    }, outfile, cls=ComplexEncoder, indent=4)
outfile.close()

oDesktop.AddMessage("", "", 0, "Done exporting PI model results (%s)" % time.asctime(time.localtime()))
