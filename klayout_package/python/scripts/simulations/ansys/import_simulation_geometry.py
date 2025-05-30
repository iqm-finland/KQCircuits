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


# This is a Python 2.7 script that should be run in Ansys Electronic Desktop in order to import and run the simulation
import time
import os
import sys
import json
import ScriptEnv

# TODO: Figure out how to set the python path for the Ansys internal IronPython
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "util"))
from geometry import (  # pylint: disable=wrong-import-position
    create_box,
    create_rectangle,
    create_polygon,
    thicken_sheet,
    set_material,
    add_layer,
    subtract,
    move_vertically,
    delete,
    add_material,
    color_by_material,
    set_color,
    scale,
    match_layer,
)
from field_calculation import (  # pylint: disable=wrong-import-position
    add_squared_electric_field_expression,
    add_energy_integral_expression,
    add_magnetic_flux_integral_expression,
)

# pylint: disable=consider-using-f-string
# Set up environment
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.AddMessage("", "", 0, "Starting import script (%s)" % time.asctime(time.localtime()))

# Import metadata (bounding box and port information)
jsonfile = ScriptArgument
path = os.path.dirname(jsonfile)

with open(jsonfile, "r") as fjsonfile:  # pylint: disable=unspecified-encoding
    data = json.load(fjsonfile)

ansys_tool = data.get("ansys_tool", "hfss")

simulation_flags = data["simulation_flags"]
gds_file = data["gds_file"]
units = data.get("units", "um")
material_dict = data.get("material_dict", {})
box = data["box"]

ansys_project_template = data.get("ansys_project_template", "")
vertical_over_etching = data.get("vertical_over_etching", 0)
mesh_size = data.get("mesh_size", {})

# Create project
oDesktop.RestoreWindow()
oProject = oDesktop.NewProject()
oDefinitionManager = oProject.GetDefinitionManager()

hfss_tools = {"hfss", "current", "voltage", "eigenmode"}

design_name = ansys_tool.capitalize() + "Design"
if ansys_tool == "eigenmode":
    oProject.InsertDesign("HFSS", design_name, "Eigenmode", "")
    oDesign = oProject.SetActiveDesign(design_name)
elif ansys_tool in hfss_tools:
    oProject.InsertDesign("HFSS", design_name, "HFSS Terminal Network", "")
    oDesign = oProject.SetActiveDesign(design_name)
elif ansys_tool == "q3d":
    oProject.InsertDesign("Q3D Extractor", design_name, "", "")
    oDesign = oProject.SetActiveDesign(design_name)

oEditor = oDesign.SetActiveEditor("3D Modeler")
oBoundarySetup = oDesign.GetModule("BoundarySetup")
oAnalysisSetup = oDesign.GetModule("AnalysisSetup")
oOutputVariable = oDesign.GetModule("OutputVariable")
oSolutions = oDesign.GetModule("Solutions")
oReportSetup = oDesign.GetModule("ReportSetup")

# Set units
oEditor.SetModelUnits(["NAME:Units Parameter", "Units:=", units, "Rescale:=", False])

# Add materials
for name, params in material_dict.items():
    add_material(oDefinitionManager, name, **params)

# Import GDSII geometry
layers = data.get("layers", {})
refine_layers = [n for n in layers if any(match_layer(n, p) for p in mesh_size)]
layers = {n: d for n, d in layers.items() if not n.endswith("_gap") or n in refine_layers}  # ignore unused gap layers
metal_layers = {n: d for n, d in layers.items() if "excitation" in d}

order_map = []
layer_map = ["NAME:LayerMap"]
order = 0
for lname, ldata in layers.items():
    if "layer" in ldata:
        add_layer(layer_map, order_map, ldata["layer"], lname, order)
        order += 1

oEditor.ImportGDSII(
    [
        "NAME:options",
        "FileName:=",
        os.path.join(path, gds_file),
        "FlattenHierarchy:=",
        True,
        "ImportMethod:=",
        1,
        layer_map,
        "OrderMap:=",
        order_map,
        ["NAME:Structs", ["NAME:GDSIIStruct", "ImportStruct:=", True, "CreateNewCell:=", True, "StructName:=", "SIM1"]],
    ]
)
scale(oEditor, oEditor.GetObjectsInGroup("Sheets"), data["gds_scaling"])

# Create 3D geometry
objects = {}
metal_sheets = []
for lname, ldata in layers.items():
    z = ldata.get("z", 0.0)
    thickness = ldata.get("thickness", 0.0)
    if "layer" in ldata:
        # Get imported objects
        objects[lname] = [n for n in oEditor.GetMatchedObjectName(lname + "_*") if n[len(lname) + 1 :].isdigit()]
        move_vertically(oEditor, objects[lname], z, units)
        thicken_sheet(oEditor, objects[lname], thickness, units)
    else:
        # Create object covering full box
        objects[lname] = [lname]
        if thickness != 0.0:
            create_box(
                oEditor,
                lname,
                box["p1"]["x"],
                box["p1"]["y"],
                z,
                box["p2"]["x"] - box["p1"]["x"],
                box["p2"]["y"] - box["p1"]["y"],
                thickness,
                units,
            )
        else:
            create_rectangle(
                oEditor,
                lname,
                box["p1"]["x"],
                box["p1"]["y"],
                z,
                box["p2"]["x"] - box["p1"]["x"],
                box["p2"]["y"] - box["p1"]["y"],
                "Z",
                units,
            )

    # Set material
    material = ldata.get("material")
    if thickness != 0.0:
        # Solve Inside parameter must be set in hfss_tools simulations to avoid warnings.
        # Solve Inside doesn't exist in 'q3d', so we use None to ignore the parameter.
        solve_inside = lname not in metal_layers if ansys_tool in hfss_tools else None
        set_material(oEditor, objects[lname], material, solve_inside)
    elif lname in metal_layers:  # is metal
        metal_sheets += objects[lname]
    elif lname not in refine_layers:
        set_material(oEditor, objects[lname], None, None)  # set sheet as non-model

    set_color(oEditor, objects[lname], *color_by_material(material, material_dict, thickness == 0.0))

# Assign perfect electric conductor to metal sheets
if metal_sheets:
    if ansys_tool in hfss_tools:
        oBoundarySetup.AssignPerfectE(["NAME:PerfE1", "Objects:=", metal_sheets, "InfGroundPlane:=", False])
    elif ansys_tool == "q3d":
        oBoundarySetup.AssignThinConductor(
            [
                "NAME:ThinCond1",
                "Objects:=",
                metal_sheets,
                "Material:=",
                "pec",
                "Thickness:=",
                "1nm",  # thickness does not matter when material is pec
            ]
        )


# Subtract objects from others. Each tool layer subtraction is performed before it's used as tool for other subtraction.
need_subtraction = [n for n, d in layers.items() if "subtract" in d]
while need_subtraction:
    for name in need_subtraction:
        if not any(s in need_subtraction for s in layers[name]["subtract"]):
            subtract(oEditor, objects[name], [o for n in layers[name]["subtract"] for o in objects[n]], True)
            need_subtraction = [s for s in need_subtraction if s != name]
            break
    else:
        oDesktop.AddMessage("", "", 0, "Encountered circular subtractions in layers {}.".format(need_subtraction))
        break


# Create ports or nets
if ansys_tool in hfss_tools:
    ports = sorted(data["ports"], key=lambda k: k["number"])
    for port in ports:
        is_wave_port = port["type"] == "EdgePort"
        if not is_wave_port or not ansys_project_template:
            if "polygon" not in port:
                continue

            polyname = "Port%d" % port["number"]

            # Create polygon spanning the two edges
            create_polygon(oEditor, polyname, [list(p) for p in port["polygon"]], units)
            set_color(oEditor, [polyname], 240, 180, 180, 0.8)

            if ansys_tool == "hfss":
                ground_objects = [o for n, d in metal_layers.items() if d["excitation"] == 0 for o in objects[n]]
                oBoundarySetup.AutoIdentifyPorts(
                    ["NAME:Faces", int(oEditor.GetFaceIDs(polyname)[0])],
                    is_wave_port,
                    ["NAME:ReferenceConductors"] + ground_objects,
                    str(port["number"]),
                    False,
                )

                renorm = port.get("renormalization", None)
                oBoundarySetup.SetTerminalReferenceImpedances(
                    "" if renorm is None else "{}ohm".format(renorm), str(port["number"]), renorm is not None
                )

                deembed_len = port.get("deembed_len", None)
                if deembed_len is not None:
                    oBoundarySetup.EditWavePort(
                        str(port["number"]),
                        [
                            "Name:%d" % port["number"],
                            "DoDeembed:=",
                            True,
                            "DeembedDist:=",
                            "%f%s" % (deembed_len, units),
                        ],
                    )

            elif ansys_tool == "current":
                oBoundarySetup.AssignCurrent(
                    [
                        "NAME:{}".format(polyname),
                        "Objects:=",
                        [polyname],
                        [
                            "NAME:Direction",
                            "Coordinate System:=",
                            "Global",
                            "Start:=",
                            ["%.32e%s" % (p, units) for p in port["signal_location"]],
                            "End:=",
                            ["%.32e%s" % (p, units) for p in port["ground_location"]],
                        ],
                    ]
                )
            elif ansys_tool == "voltage":
                oBoundarySetup.AssignVoltage(
                    [
                        "NAME:{}".format(polyname),
                        "Objects:=",
                        [polyname],
                        [
                            "NAME:Direction",
                            "Coordinate System:=",
                            "Global",
                            "Start:=",
                            ["%.32e%s" % (p, units) for p in port["signal_location"]],
                            "End:=",
                            ["%.32e%s" % (p, units) for p in port["ground_location"]],
                        ],
                    ]
                )

            elif port["junction"] and ansys_tool == "eigenmode":
                # add junction inductance variable
                oDesign.ChangeProperty(
                    [
                        "NAME:AllTabs",
                        [
                            "NAME:LocalVariableTab",
                            ["NAME:PropServers", "LocalVariables"],
                            [
                                "NAME:NewProps",
                                [
                                    "NAME:Lj_%d" % port["number"],
                                    "PropType:=",
                                    "VariableProp",
                                    "UserDef:=",
                                    True,
                                    "Value:=",
                                    "%.32eH" % port["inductance"],
                                ],  # use best float precision
                            ],
                        ],
                    ]
                )
                # add junction capacitance variable
                oDesign.ChangeProperty(
                    [
                        "NAME:AllTabs",
                        [
                            "NAME:LocalVariableTab",
                            ["NAME:PropServers", "LocalVariables"],
                            [
                                "NAME:NewProps",
                                [
                                    "NAME:Cj_%d" % port["number"],
                                    "PropType:=",
                                    "VariableProp",
                                    "UserDef:=",
                                    True,
                                    "Value:=",
                                    "%.32efarad" % port["capacitance"],
                                ],
                            ],
                        ],
                    ]
                )

                # Turn junctions to lumped RLC
                current_start = ["%.32e%s" % (p, units) for p in port["signal_location"]]
                current_end = ["%.32e%s" % (p, units) for p in port["ground_location"]]
                oBoundarySetup.AssignLumpedRLC(
                    [
                        "NAME:LumpRLC_jj_%d" % port["number"],
                        "Objects:=",
                        [polyname],
                        [
                            "NAME:CurrentLine",  # set direction of current across junction
                            "Coordinate System:=",
                            "Global",
                            "Start:=",
                            current_start,
                            "End:=",
                            current_end,
                        ],
                        "RLC Type:=",
                        "Parallel",
                        "UseResist:=",
                        False,
                        "UseInduct:=",
                        True,
                        "Inductance:=",
                        "Lj_%d" % port["number"],
                        "UseCap:=",
                        True,
                        "Capacitance:=",
                        "Cj_%d" % port["number"],
                        "Faces:=",
                        [int(oEditor.GetFaceIDs(polyname)[0])],
                    ]
                )

                if "pyepr" in simulation_flags:
                    # add polyline across junction for voltage across the junction
                    oEditor.CreatePolyline(
                        [
                            "NAME:PolylineParameters",
                            "IsPolylineCovered:=",
                            True,
                            "IsPolylineClosed:=",
                            False,
                            [
                                "NAME:PolylinePoints",
                                [
                                    "NAME:PLPoint",
                                    "X:=",
                                    current_start[0],
                                    "Y:=",
                                    current_start[1],
                                    "Z:=",
                                    current_start[2],
                                ],
                                ["NAME:PLPoint", "X:=", current_end[0], "Y:=", current_end[1], "Z:=", current_end[2]],
                            ],
                            [
                                "NAME:PolylineSegments",
                                ["NAME:PLSegment", "SegmentType:=", "Line", "StartIndex:=", 0, "NoOfPoints:=", 2],
                            ],
                            [
                                "NAME:PolylineXSection",
                                "XSectionType:=",
                                "None",
                                "XSectionOrient:=",
                                "Auto",
                                "XSectionWidth:=",
                                "0" + units,
                                "XSectionTopWidth:=",
                                "0" + units,
                                "XSectionHeight:=",
                                "0" + units,
                                "XSectionNumSegments:=",
                                "0",
                                "XSectionBendType:=",
                                "Corner",
                            ],
                        ],
                        [
                            "NAME:Attributes",
                            "Name:=",
                            "Junction%d" % port["number"],
                            "Flags:=",
                            "",
                            "Color:=",
                            "(143 175 143)",
                            "Transparency:=",
                            0.4,
                            "PartCoordinateSystem:=",
                            "Global",
                            "UDMId:=",
                            "",
                            "MaterialValue:=",
                            '"vacuum"',
                            "SurfaceMaterialValue:=",
                            '""',
                            "SolveInside:=",
                            True,
                            "ShellElement:=",
                            False,
                            "ShellElementThickness:=",
                            "0" + units,
                            "IsMaterialEditable:=",
                            True,
                            "UseMaterialAppearance:=",
                            False,
                            "IsLightweight:=",
                            False,
                        ],
                    )

                    oEditor.ChangeProperty(
                        [
                            "NAME:AllTabs",
                            [
                                "NAME:Geometry3DAttributeTab",
                                ["NAME:PropServers", "Junction%d" % port["number"]],
                                ["NAME:ChangedProps", ["NAME:Show Direction", "Value:=", True]],
                            ],
                        ]
                    )


elif ansys_tool == "q3d":
    excitations = {d["excitation"] for d in metal_layers.values()}
    for excitation in excitations:
        objs = [o for n, d in metal_layers.items() if d["excitation"] == excitation for o in objects[n]]
        if not objs:
            continue
        if excitation == 0:
            for i, obj in enumerate(objs):
                oBoundarySetup.AssignGroundNet(["NAME:Ground{}".format(i + 1), "Objects:=", [obj]])
        elif excitation is None:
            for i, obj in enumerate(objs):
                oBoundarySetup.AssignFloatingNet(["NAME:Floating{}".format(i + 1), "Objects:=", [obj]])
        else:
            oBoundarySetup.AssignSignalNet(["NAME:Net{}".format(excitation), "Objects:=", objs])
    oBoundarySetup.AutoIdentifyNets()  # Combine Nets by conductor connections. Order: GroundNet, SignalNet, FloatingNet


# Add field calculations
if data.get("integrate_energies", False) and ansys_tool in hfss_tools:
    # Create term for squared E fields
    oModule = oDesign.GetModule("FieldsReporter")
    add_squared_electric_field_expression(oModule, "Esq", "Mag")
    add_squared_electric_field_expression(oModule, "Ezsq", "ScalarZ")

    # Create energy integral terms for each object
    epsilon_0 = 8.8541878128e-12
    for lname, ldata in layers.items():
        if lname in metal_layers:
            continue

        thickness = ldata.get("thickness", 0.0)
        if thickness == 0.0:
            add_energy_integral_expression(oModule, "Ez_{}".format(lname), objects[lname], "Ezsq", 2, epsilon_0, "")
            add_energy_integral_expression(
                oModule, "Exy_{}".format(lname), objects[lname], "Esq", 2, epsilon_0, "Ez_{}".format(lname)
            )
        else:
            material = ldata.get("material", None)
            if material is not None:
                epsilon = epsilon_0 * material_dict.get(material, {}).get("permittivity", 1.0)
                add_energy_integral_expression(oModule, "E_{}".format(lname), objects[lname], "Esq", 3, epsilon, "")

if data.get("integrate_magnetic_flux", False) and ansys_tool in hfss_tools:
    oModule = oDesign.GetModule("FieldsReporter")
    for lname, ldata in layers.items():
        if ldata.get("thickness", 0.0) != 0.0 or lname in metal_layers:
            continue

        add_magnetic_flux_integral_expression(oModule, "flux_{}".format(lname), objects[lname])

# Manual mesh refinement
for mesh_name, mesh_length in mesh_size.items():
    mesh_layers = [n for n in layers if match_layer(n, mesh_name)]
    mesh_objects = [o for l in mesh_layers if l in objects for o in objects[l]]
    if mesh_objects:
        oMeshSetup = oDesign.GetModule("MeshSetup")
        oMeshSetup.AssignLengthOp(
            [
                "NAME:mesh_size_{}".format(mesh_name),
                "RefineInside:=",
                all(layers[n].get("thickness", 0.0) != 0.0 for n in mesh_layers),
                "Enabled:=",
                True,
                "Objects:=",
                mesh_objects,
                "RestrictElem:=",
                False,
                "RestrictLength:=",
                True,
                "MaxLength:=",
                str(mesh_length) + units,
            ]
        )

if not ansys_project_template:
    # Insert analysis setup
    setup = data["analysis_setup"]

    if ansys_tool == "hfss":
        # create setup_list for analysis setup with TWO OPTIONS: multiple frequency or single frequency
        multiple_frequency = isinstance(setup["frequency"], list)
        setup_list = ["NAME:Setup1", "AdaptMultipleFreqs:=", multiple_frequency]

        if multiple_frequency:
            max_delta_s = setup["max_delta_s"]
            if not isinstance(type(max_delta_s), list):
                max_delta_s = [max_delta_s] * len(setup["frequency"])  # make max_delta_s a list
            maf_setup_list = ["NAME:MultipleAdaptiveFreqsSetup"]
            for f, s in zip(setup["frequency"], max_delta_s):
                maf_setup_list += [str(f) + setup["frequency_units"] + ":=", [s]]
            setup_list += [maf_setup_list]
        else:
            setup_list += [
                "Frequency:=",
                str(setup["frequency"]) + setup["frequency_units"],
                "MaxDeltaS:=",
                setup["max_delta_s"],
            ]

        setup_list += [
            "MaximumPasses:=",
            setup["maximum_passes"],
            "MinimumPasses:=",
            setup["minimum_passes"],
            "MinimumConvergedPasses:=",
            setup["minimum_converged_passes"],
            "PercentRefinement:=",
            setup["percent_refinement"],
            "IsEnabled:=",
            True,
            ["NAME:MeshLink", "ImportMesh:=", False],
            "BasisOrder:=",
            1,
            "DoLambdaRefine:=",
            True,
            "DoMaterialLambda:=",
            True,
            "SetLambdaTarget:=",
            False,
            "Target:=",
            0.3333,
            "UseMaxTetIncrease:=",
            False,
            "PortAccuracy:=",
            0.2,
            "UseABCOnPort:=",
            False,
            "SetPortMinMaxTri:=",
            False,
            "UseDomains:=",
            False,
            "UseIterativeSolver:=",
            False,
            "SaveRadFieldsOnly:=",
            False,
            "SaveAnyFields:=",
            True,
            "IESolverType:=",
            "Auto",
            "LambdaTargetForIESolver:=",
            0.15,
            "UseDefaultLambdaTgtForIESolver:=",
            True,
        ]
        oAnalysisSetup.InsertSetup("HfssDriven", setup_list)

        oAnalysisSetup.InsertFrequencySweep(
            "Setup1",
            [
                "NAME:Sweep",
                "IsEnabled:=",
                setup["sweep_enabled"],
                "RangeType:=",
                "LinearCount",
                "RangeStart:=",
                str(setup["sweep_start"]) + setup["frequency_units"],
                "RangeEnd:=",
                str(setup["sweep_end"]) + setup["frequency_units"],
                "RangeCount:=",
                setup["sweep_count"],
                "Type:=",
                setup["sweep_type"],
                "SaveFields:=",
                False,
                "SaveRadFields:=",
                False,
                "InterpTolerance:=",
                0.5,
                "InterpMaxSolns:=",
                250,
                "InterpMinSolns:=",
                0,
                "InterpMinSubranges:=",
                1,
                "ExtrapToDC:=",
                setup["sweep_start"] == 0,
                "MinSolvedFreq:=",
                "0.01GHz",
                "InterpUseS:=",
                True,
                "InterpUsePortImped:=",
                True,
                "InterpUsePropConst:=",
                True,
                "UseDerivativeConvergence:=",
                False,
                "InterpDerivTolerance:=",
                0.2,
                "UseFullBasis:=",
                True,
                "EnforcePassivity:=",
                True,
                "PassivityErrorTolerance:=",
                0.0001,
                "EnforceCausality:=",
                False,
            ],
        )
    elif ansys_tool in ["current", "voltage"]:
        oAnalysisSetup.InsertSetup(
            "HfssDriven",
            [
                "NAME:Setup1",
                "SolveType:=",
                "Single",
                "Frequency:=",
                str(setup["frequency"]) + setup["frequency_units"],
                "MaxDeltaE:=",
                setup["max_delta_e"],
                "MaximumPasses:=",
                setup["maximum_passes"],
                "MinimumPasses:=",
                setup["minimum_passes"],
                "MinimumConvergedPasses:=",
                setup["minimum_converged_passes"],
                "PercentRefinement:=",
                setup["percent_refinement"],
                "IsEnabled:=",
                True,
                ["NAME:MeshLink", "ImportMesh:=", False],
                "BasisOrder:=",
                1,
                "DoLambdaRefine:=",
                True,
                "DoMaterialLambda:=",
                True,
                "SetLambdaTarget:=",
                False,
                "Target:=",
                0.3333,
                "UseMaxTetIncrease:=",
                False,
                "DrivenSolverType:=",
                "Direct Solver",
                "EnhancedLowFreqAccuracy:=",
                False,
                "SaveRadFieldsOnly:=",
                False,
                "SaveAnyFields:=",
                True,
                "IESolverType:=",
                "Auto",
                "LambdaTargetForIESolver:=",
                0.15,
                "UseDefaultLambdaTgtForIESolver:=",
                True,
                "IE Solver Accuracy:=",
                "Balanced",
                "InfiniteSphereSetup:=",
                "",
            ],
        )
    elif ansys_tool == "q3d":
        oAnalysisSetup.InsertSetup(
            "Matrix",
            [
                "NAME:Setup1",
                "AdaptiveFreq:=",
                str(setup["frequency"]) + setup["frequency_units"],
                "SaveFields:=",
                False,
                "Enabled:=",
                True,
                [
                    "NAME:Cap",
                    "MaxPass:=",
                    setup["maximum_passes"],
                    "MinPass:=",
                    setup["minimum_passes"],
                    "MinConvPass:=",
                    setup["minimum_converged_passes"],
                    "PerError:=",
                    setup["percent_error"],
                    "PerRefine:=",
                    setup["percent_refinement"],
                    "AutoIncreaseSolutionOrder:=",
                    True,
                    "SolutionOrder:=",
                    "High",
                    "Solver Type:=",
                    "Iterative",
                ],
            ],
        )
    elif ansys_tool == "eigenmode":
        # Create EM setup
        setup_list = [
            "NAME:Setup1",
            "MinimumFrequency:=",
            str(setup["min_frequency"]) + setup["frequency_units"],
            "NumModes:=",
            setup["n_modes"],
            "MaxDeltaFreq:=",
            setup["max_delta_f"],
            "ConvergeOnRealFreq:=",
            True,
            "MaximumPasses:=",
            setup["maximum_passes"],
            "MinimumPasses:=",
            setup["minimum_passes"],
            "MinimumConvergedPasses:=",
            setup["minimum_converged_passes"],
            "PercentRefinement:=",
            setup["percent_refinement"],
            "IsEnabled:=",
            True,
            "BasisOrder:=",
            1,
        ]
        oAnalysisSetup.InsertSetup("HfssEigen", setup_list)

else:  # use ansys_project_template
    # delete substrate and vacuum objects
    delete(oEditor, [o for n, v in objects.items() if "substrate" in n or "vacuum" in n for o in v])

    scriptpath = os.path.dirname(__file__)
    aedt_path = os.path.join(scriptpath, "../")
    basename = os.path.splitext(os.path.basename(jsonfile))[0]
    build_geom_name = basename + "_build_geometry"
    template_path = data["ansys_project_template"]
    template_basename = os.path.splitext(os.path.basename(template_path))[0]

    oProject = oDesktop.GetActiveProject()
    oProject.SaveAs(os.path.join(aedt_path, build_geom_name + ".aedt"), True)

    oDesign = oProject.GetActiveDesign()
    oEditor = oDesign.SetActiveEditor("3D Modeler")
    sheet_name_list = oEditor.GetObjectsInGroup("Sheets") + oEditor.GetObjectsInGroup("Solids")
    oEditor.Copy(["NAME:Selections", "Selections:=", ",".join(sheet_name_list)])

    oDesktop.OpenProject(os.path.join(aedt_path, template_path))
    oProject = oDesktop.SetActiveProject(template_basename)
    oDesign = oProject.GetActiveDesign()
    oEditor = oDesign.SetActiveEditor("3D Modeler")
    oEditor.Paste()
    oDesktop.CloseProject(build_geom_name)


# Fit window to objects
oEditor.FitAll()

# Notify the end of script
oDesktop.AddMessage("", "", 0, "Import completed (%s)" % time.asctime(time.localtime()))
# pylint: enable=consider-using-f-string
