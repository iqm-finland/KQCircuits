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


# This is a Python 2.7 script that should be run in HFSS in order to export solution data
import time
import os
import sys
import json
import ScriptEnv

# TODO: Figure out how to set the python path for the HFSS internal IronPython
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "util"))
from util import (  # pylint: disable=wrong-import-position,no-name-in-module
    get_enabled_setup,
    get_enabled_sweep,
    get_solution_data,
    get_quantities,
    ComplexEncoder,
)


# pylint: disable=consider-using-f-string
def save_capacitance_matrix(file_name, c_matrix, detail=""):
    """Save capacitance matrix in readable format."""
    with open(file_name, "w") as out_file:  # pylint: disable=unspecified-encoding
        out_file.write(
            "Capacitance matrix"
            + detail
            + ":\n"
            + "\n".join(["\t".join(["%8.3f" % (item * 1e15) for item in row]) for row in c_matrix])
            + "\n"
        )


# Set up environment
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.AddMessage("", "", 0, "Exporting solution data (%s)" % time.asctime(time.localtime()))

oDesktop.RestoreWindow()
oProject = oDesktop.GetActiveProject()
oDesign = oProject.GetActiveDesign()
oSolutions = oDesign.GetModule("Solutions")
oBoundarySetup = oDesign.GetModule("BoundarySetup")
oOutputVariable = oDesign.GetModule("OutputVariable")
oReportSetup = oDesign.GetModule("ReportSetup")

# Set file names
path = oProject.GetPath()
basename = oProject.GetName()
matrix_filename = os.path.join(path, basename + "_CMatrix.txt")
json_filename = os.path.join(path, basename + "_results.json")
json_content = {}
eig_filename = os.path.join(path, basename + "_modes.eig")
energy_filename = os.path.join(path, basename + "_energy.csv")
flux_filename = os.path.join(path, basename + "_flux.csv")

# Export solution data separately for HFSS and Q3D
design_type = oDesign.GetDesignType()
if design_type == "HFSS":
    setup = get_enabled_setup(oDesign)
    solution = setup + " : LastAdaptive"
    context = []
    if oDesign.GetSolutionType() == "HFSS Terminal Network":
        sweep = get_enabled_sweep(oDesign, setup)
        ports = oBoundarySetup.GetExcitations()[::2]

        # Capacitance matrix export
        output_variables = oOutputVariable.GetOutputVariables()
        if all("C_{}_{}".format(i, j) in output_variables for j in ports for i in ports):
            # find lowest-frequency solution (of LastAdaptive) for capacitance extraction
            res = oReportSetup.GetSolutionDataPerVariation(
                "Terminal Solution Data", solution, context, ["Freq:=", ["All"]], [""]
            )[0]
            freq = "{}{}".format(res.GetSweepValues("Freq", False)[0], res.GetSweepUnits("Freq"))
            families = ["Freq:=", [freq]]

            # Create content for result json file
            json_content = {
                "CMatrix": [
                    [
                        get_solution_data(
                            oReportSetup, "Terminal Solution Data", solution, context, families, "C_{}_{}".format(i, j)
                        )[0]
                        for j in ports
                    ]
                    for i in ports
                ],
                "yyMatrix": [
                    [
                        get_solution_data(
                            oReportSetup, "Terminal Solution Data", solution, context, families, "yy_{}_{}".format(i, j)
                        )[0]
                        for j in ports
                    ]
                    for i in ports
                ],
                "freq": freq,
                "yydata": get_solution_data(
                    oReportSetup,
                    "Terminal Solution Data",
                    solution,
                    context,
                    families,
                    ["yy_{}_{}".format(i, j) for i in ports for j in ports],
                ),
                "Cdata": get_solution_data(
                    oReportSetup,
                    "Terminal Solution Data",
                    solution,
                    context,
                    families,
                    ["C_{}_{}".format(i, j) for i in ports for j in ports],
                ),
            }

            # Save capacitance matrix into readable format
            save_capacitance_matrix(matrix_filename, json_content["CMatrix"], detail=" at " + freq)

        # S-parameter export
        s_solution = solution if sweep is None else setup + " : " + sweep
        s_context = context if sweep is None else ["Domain:=", "Sweep"]
        if get_quantities(oReportSetup, "Terminal Solution Data", s_solution, s_context, "Terminal S Parameter"):
            file_name = os.path.join(path, basename + "_SMatrix.s{}p".format(len(ports)))
            oSolutions.ExportNetworkData(
                "",  # Design variation key. Pass empty string for the current nominal variation.
                s_solution,  # Selected solutions
                3,  # File format: 2 = Tab delimited (.tab), 3 = Touchstone (.sNp), 4 = CitiFile (.cit), 7 = Matlab (.m)
                file_name,  # Full path to the file to write out
                ["All"],  # The frequencies to export. Use ["All"] to export all available frequencies
                False,  # Specifies whether to renormalize the data before export
                50,  # Real impedance value in ohms, for renormalization
                "S",  # The matrix to export. "S", "Y", or "Z"
                -1,  # The pass to export. Specifying -1 gets all available passes
                0,  # Format of complex numbers: 0 = magnitude/phase, 1 = real/imag, 2 = dB/phase
                15,  # Touchstone number of digits precision
                True,  # Specifies whether to use export frequencies
                False,  # Specifies whether to include Gamma and Impedance comments
                True,  # Specifies whether to support non-standard Touchstone extensions for mixed reference impedance
            )

    elif oDesign.GetSolutionType() == "Eigenmode":
        oSolutions.ExportEigenmodes(solution, oSolutions.ListVariations(solution)[0], eig_filename)

    # Add integrals to result json file
    json_content.update(
        {
            e: get_solution_data(oReportSetup, "Fields", solution, context, ["Phase:=", ["0deg"]], e)[0]
            for e in get_quantities(oReportSetup, "Fields", solution, context, "Calculator Expressions")
        }
    )

    # Save energy integrals
    report_names = oReportSetup.GetAllReportNames()
    if "Energy Integrals" in report_names:
        oReportSetup.ExportToFile("Energy Integrals", energy_filename, False)

    # Save magnetic flux integrals
    report_names = oReportSetup.GetAllReportNames()
    if "Magnetic Fluxes" in report_names:
        oReportSetup.ExportToFile("Magnetic Fluxes", flux_filename, False)

elif design_type == "Q3D Extractor":
    setup = get_enabled_setup(oDesign, tab="General")
    solution = setup + " : LastAdaptive"
    context = ["Context:=", "Original"]

    # Get list of signal nets
    nets = oBoundarySetup.GetExcitations()[::2]
    net_types = oBoundarySetup.GetExcitations()[1::2]
    signal_nets = [net for net, net_type in zip(nets, net_types) if net_type == "SignalNet"]

    # Create content for result json file
    json_content = {
        "CMatrix": [
            [
                get_solution_data(oReportSetup, "Matrix", solution, context, [], "C_{}_{}".format(net_i, net_j))[0]
                for net_j in signal_nets
            ]
            for net_i in signal_nets
        ],
        "Cdata": get_solution_data(
            oReportSetup,
            "Matrix",
            solution,
            context,
            [],
            ["C_{}_{}".format(net_i, net_j) for net_j in signal_nets for net_i in signal_nets],
        ),
    }

    # Save capacitance matrix into readable format
    save_capacitance_matrix(matrix_filename, json_content["CMatrix"])

elif design_type == "2D Extractor":
    setup = get_enabled_setup(oDesign, tab="General")
    solution = setup + " : LastAdaptive"
    context = ["Context:=", "Original"]

    conductors = oBoundarySetup.GetExcitations()[::2]
    conductor_types = oBoundarySetup.GetExcitations()[1::2]
    signals = sorted([c for c, c_type in zip(conductors, conductor_types) if c_type == "SignalLine"])

    # Create content for result json file
    json_content = {
        "Cs": [
            [
                get_solution_data(oReportSetup, "Matrix", solution, context, [], "C_%s_%s" % (s_i, s_j))[0]
                for s_j in signals
            ]
            for s_i in signals
        ],
        "Ls": [
            [
                get_solution_data(oReportSetup, "Matrix", solution, context, [], "L(%s,%s)" % (s_i, s_j))[0]
                for s_j in signals
            ]
            for s_i in signals
        ],
        "Z0": [
            [
                get_solution_data(oReportSetup, "Matrix", solution, context, [], "mag(Z0({},{}))".format(s_i, s_j))[0]
                for s_j in signals
            ]
            for s_i in signals
        ],
        "c_eff": [
            get_solution_data(oReportSetup, "Matrix", solution, context, [], s)[0]
            for s in get_quantities(oReportSetup, "Matrix", solution, context, "Velocity")
        ],
    }
    json_content.update(
        {
            e: get_solution_data(oReportSetup, "CG Fields", solution, context, ["Phase:=", ["0deg"]], e)[0]
            for e in get_quantities(oReportSetup, "CG Fields", solution, context, "Calculator Expressions")
        }
    )

    # Save energy integrals
    report_names = oReportSetup.GetAllReportNames()
    if "Energy Integrals" in report_names:
        oReportSetup.ExportToFile("Energy Integrals", energy_filename, False)

# Save results in json format
if json_content:
    with open(json_filename, "w") as outfile:  # pylint: disable=unspecified-encoding
        json.dump(json_content, outfile, cls=ComplexEncoder, indent=4)

# Notify the end of script
oDesktop.AddMessage("", "", 0, "Done exporting solution data (%s)" % time.asctime(time.localtime()))
# pylint: enable=consider-using-f-string
