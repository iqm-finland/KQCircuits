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


# This is a Python 2.7 script that should be run in Ansys Electronic Desktop in order to import and run the simulation
from math import cos, pi
import time
import os
import sys
import json
import ScriptEnv

# TODO: Figure out how to set the python path for the Ansys internal IronPython
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "util"))
# fmt: off
from geometry import create_box, create_rectangle, create_polygon, thicken_sheet, set_material, add_layer, subtract, \
    move_vertically, delete, objects_from_sheet_edges, add_material, set_color  # pylint: disable=wrong-import-position
from field_calculation import add_squared_electric_field_expression,  add_energy_integral_expression, \
    add_magnetic_flux_integral_expression  # pylint: disable=wrong-import-position
# fmt: on

# Set up environment
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.AddMessage("", "", 0, "Starting import script (%s)" % time.asctime(time.localtime()))

# Import metadata (bounding box and port information)
jsonfile = ScriptArgument
path = os.path.dirname(jsonfile)

with open(jsonfile, "r") as fjsonfile:
    data = json.load(fjsonfile)

ansys_tool = data.get("ansys_tool", "hfss")

simulation_flags = data["simulation_flags"]
gds_file = data["gds_file"]
units = data.get("units", "um")
material_dict = data.get("material_dict", dict())
box = data["box"]

ansys_project_template = data.get("ansys_project_template", "")
vertical_over_etching = data.get("vertical_over_etching", 0)
mesh_size = data.get("mesh_size", dict())

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


# Define colors
def color_by_material(material, is_sheet=False):
    if material == "pec":
        return 240, 120, 240, 0.5
    n = 0.3 * (material_dict.get(material, dict()).get("permittivity", 1.0) - 1.0)
    alpha = 0.93 ** (2 * n if is_sheet else n)
    return tuple(int(100 + 80 * c) for c in [cos(n - pi / 3), cos(n + pi), cos(n + pi / 3)]) + (alpha,)


# Set units
oEditor.SetModelUnits(["NAME:Units Parameter", "Units:=", units, "Rescale:=", False])

# Add materials
for name, params in material_dict.items():
    add_material(oDefinitionManager, name, **params)

# Import GDSII geometry
layers = data.get("layers", dict())
# ignore gap objects if they are not used
layers = {n: d for n, d in layers.items() if "_gap" not in n or n in mesh_size}

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

# Create 3D geometry
objects = {}
pec_sheets = []
for lname, ldata in layers.items():
    z = ldata.get("z", 0.0)
    thickness = ldata.get("thickness", 0.0)
    if "layer" in ldata:
        # Get imported objects
        objects[lname] = oEditor.GetMatchedObjectName(lname + "_*")
        move_vertically(oEditor, objects[lname], z, units)

        # Create pec-sheets from edges
        edge_material = ldata.get("edge_material", None)
        if edge_material == "pec" and thickness != 0.0:
            pec_sheets += objects_from_sheet_edges(oEditor, objects[lname], thickness, units)

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
    material = ldata.get("material", None)
    if thickness != 0.0:
        # Solve Inside parameter must be set in hfss_tools simulations to avoid warnings.
        # Solve Inside doesn't exist in 'q3d', so we use None to ignore the parameter.
        solve_inside = material != "pec" if ansys_tool in hfss_tools else None
        set_material(oEditor, objects[lname], material, solve_inside)
        set_color(oEditor, objects[lname], *color_by_material(material))
    elif material == "pec":
        pec_sheets += objects[lname]
    else:
        set_color(oEditor, objects[lname], *color_by_material(material, True))
        if lname not in mesh_size:
            set_material(oEditor, objects[lname], None, None)  # set sheet as non-model

# Assign perfect electric conductor to metal sheets
if pec_sheets:
    set_color(oEditor, pec_sheets, *color_by_material("pec", True))
    if ansys_tool in hfss_tools:
        oBoundarySetup.AssignPerfectE(["NAME:PerfE1", "Objects:=", pec_sheets, "InfGroundPlane:=", False])
    elif ansys_tool == "q3d":
        oBoundarySetup.AssignThinConductor(
            [
                "NAME:ThinCond1",
                "Objects:=",
                pec_sheets,
                "Material:=",
                "pec",
                "Thickness:=",
                "1nm",  # thickness does not matter when material is pec
            ]
        )


# Subtract objects from others
for lname, ldata in layers.items():
    if "subtract" in ldata:
        subtract(oEditor, objects[lname], [o for n in ldata["subtract"] for o in objects[n]], True)


# Create ports or nets
signal_objects = [o for n, v in objects.items() if "_signal" in n for o in v]
ground_objects = [o for n, v in objects.items() if "_ground" in n for o in v]
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
    port_objects = []  # signal objects to be assigned as SignalNets
    ports = sorted(data["ports"], key=lambda k: k["number"])
    for port in ports:
        signal_location = port["signal_location"]
        if "ground_location" in port:
            # Use 1e-2 safe margin to ensure that signal_location is inside the signal polygon:
            signal_location = [x + 1e-2 * (x - y) for x, y in zip(signal_location, port["ground_location"])]
        port_object = oEditor.GetBodyNamesByPosition(
            [
                "NAME:Parameters",
                "XPosition:=",
                str(signal_location[0]) + units,
                "YPosition:=",
                str(signal_location[1]) + units,
                "ZPosition:=",
                str(signal_location[2]) + units,
            ]
        )

        port_object = [o for o in port_object if "_signal" in o]

        if len(port_object) == 1 and port_object[0] not in port_objects and port_object[0] in signal_objects:
            port_objects.append(port_object[0])

    if not port_objects:
        port_objects = signal_objects  # port_objects is empty -> assign all signals as SignalNets without sorting

    for i, signal_object in enumerate(port_objects):
        oBoundarySetup.AssignSignalNet(["NAME:Net{}".format(i + 1), "Objects:=", [signal_object]])
    for i, floating_object in enumerate([obj for obj in signal_objects if obj not in port_objects]):
        oBoundarySetup.AssignFloatingNet(["NAME:Floating{}".format(i + 1), "Objects:=", [floating_object]])
    for i, ground_object in enumerate(ground_objects):
        oBoundarySetup.AssignGroundNet(["NAME:Ground{}".format(i + 1), "Objects:=", [ground_object]])
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
        material = ldata.get("material", None)
        if material == "pec":
            continue

        thickness = ldata.get("thickness", 0.0)
        if thickness == 0.0:
            add_energy_integral_expression(oModule, "Ez_{}".format(lname), objects[lname], "Ezsq", 2, epsilon_0, "")
            add_energy_integral_expression(
                oModule, "Exy_{}".format(lname), objects[lname], "Esq", 2, epsilon_0, "Ez_{}".format(lname)
            )
        elif material is not None:
            epsilon = epsilon_0 * material_dict.get(material, {}).get("permittivity", 1.0)
            add_energy_integral_expression(oModule, "E_{}".format(lname), objects[lname], "Esq", 3, epsilon, "")

if data.get("integrate_magnetic_flux", False) and ansys_tool in hfss_tools:
    oModule = oDesign.GetModule("FieldsReporter")
    for lname, ldata in layers.items():
        if ldata.get("thickness", 0.0) != 0.0 or ldata.get("material", None) == "pec":
            continue

        add_magnetic_flux_integral_expression(oModule, "flux_{}".format(lname), objects[lname])

# Manual mesh refinement
for mesh_layer, mesh_length in mesh_size.items():
    mesh_objects = objects.get(mesh_layer, list())
    if mesh_objects:
        oMeshSetup = oDesign.GetModule("MeshSetup")
        oMeshSetup.AssignLengthOp(
            [
                "NAME:mesh_size_{}".format(mesh_layer),
                "RefineInside:=",
                layers.get(mesh_layer, dict()).get("thickness", 0.0) != 0.0,
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
        if isinstance(type(setup["frequency"]), list):
            setup["frequency"] = setup["frequency"][0]
            oDesktop.AddMessage(
                "",
                "",
                0,
                "Multi-frequency is not supported in Q3D. Create setup with frequency "
                "{}.".format(str(setup["frequency"]) + setup["frequency_units"]),
            )

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
        min_freq_ghz = str(setup.get("frequency", 0.1)) + setup["frequency_units"]

        setup_list = [
            "NAME:Setup1",
            "MinimumFrequency:=",
            min_freq_ghz,
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
