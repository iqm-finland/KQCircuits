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
import time
import os
import sys
import json
import ScriptEnv

# TODO: Figure out how to set the python path for the Ansys internal IronPython
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'util'))
from geometry import create_box, create_polygon, thicken_sheet, add_layer, move_vertically, \
    copy_paste, objects_from_sheet_edges  # pylint: disable=wrong-import-position

# Set up environment
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.AddMessage("", "", 0, "Starting import script (%s)" % time.asctime(time.localtime()))

# Import metadata (bounding box and port information)
jsonfile = ScriptArgument
path = os.path.dirname(jsonfile)

with open(jsonfile, 'r') as fjsonfile:
    data = json.load(fjsonfile)


ansys_tool = data.get('ansys_tool', 'hfss')

simulation_flags = data['simulation_flags']
gds_file = data['gds_file']
units = data.get('units', 'um')
lower_box_height = data.get('lower_box_height', 0)
face_stack = data['face_stack']
z_levels = data['z_levels']
permittivity = data['permittivity']
airbridge_height = data.get('airbridge_height', 0)
hollow_tsv = data.get('hollow_tsv', False)

substrate_loss_tangent = data.get('substrate_loss_tangent', 0)
participation_sheet_distance = data.get('participation_sheet_distance', None)
thicken_participation_sheet_distance = data.get('thicken_participation_sheet_distance', None)
use_ansys_project_template = 'ansys_project_template' in data \
    and not data['ansys_project_template'] == ''
vertical_over_etching = data.get('vertical_over_etching', 0)
gap_max_element_length = data.get('gap_max_element_length', None)
export_gaps = any((
    vertical_over_etching > 0,
    gap_max_element_length is not None,
    participation_sheet_distance is not None
))

# Create project
oDesktop.RestoreWindow()
oProject = oDesktop.NewProject()
oDefinitionManager = oProject.GetDefinitionManager()

if ansys_tool == 'hfss':
    oProject.InsertDesign("HFSS", "HFSSDesign1", "HFSS Terminal Network", "")
    oDesign = oProject.SetActiveDesign("HFSSDesign1")
elif ansys_tool == 'eigenmode':
    oProject.InsertDesign("HFSS", "HFSSDesign1", "Eigenmode", "")
    oDesign = oProject.SetActiveDesign("HFSSDesign1")
elif ansys_tool == 'q3d':
    oProject.InsertDesign("Q3D Extractor", "Q3DDesign1", "", "")
    oDesign = oProject.SetActiveDesign("Q3DDesign1")

oEditor = oDesign.SetActiveEditor("3D Modeler")
oBoundarySetup = oDesign.GetModule("BoundarySetup")
oAnalysisSetup = oDesign.GetModule("AnalysisSetup")
oOutputVariable = oDesign.GetModule("OutputVariable")
oSolutions = oDesign.GetModule("Solutions")
oReportSetup = oDesign.GetModule("ReportSetup")

# Set units
oEditor.SetModelUnits(['NAME:Units Parameter', 'Units:=', units, 'Rescale:=', False])

# Add materials
oDefinitionManager.AddMaterial(
    ["NAME:si",
     "CoordinateSystemType:=", "Cartesian",
     "BulkOrSurfaceType:=", 1,
     ["NAME:PhysicsTypes", "set:=", ["Electromagnetic"]],
     "permittivity:=", str(permittivity),
     ] + (["dielectric_loss_tangent:=", str(substrate_loss_tangent)] if substrate_loss_tangent != 0 else [])
)

oDefinitionManager.AddMaterial(
    ["NAME:sc_metal",
     "CoordinateSystemType:=", "Cartesian",
     "BulkOrSurfaceType:=", 1,
     ["NAME:PhysicsTypes", "set:=", ["Electromagnetic"]],
     "conductivity:=", "1e+30"
     ]
)

# Import GDSII geometry
layers = data['layers']
layer_names = ['signal', 'ground', 'airbridge_flyover', 'airbridge_pads', 'indium_bump', 'tsv']
if export_gaps:
    layer_names += ['gap']

order_map = []
layer_map = ["NAME:LayerMap"]
order = 0
for face in face_stack:
    if not face:
        continue

    for layer_name in layer_names:
        full_layer_name = face + '_simulation_' + layer_name
        if full_layer_name in layers:
            dest_name = face + '_' + layer_name
            add_layer(layer_map, order_map, layers[full_layer_name], dest_name, order)
            order += 1

oEditor.ImportGDSII(
    ["NAME:options",
     "FileName:=", os.path.join(path, gds_file),
     "FlattenHierarchy:=", True,
     "ImportMethod:=", 1,
     layer_map,
     "OrderMap:=", order_map,
     ["NAME:Structs",
      ["NAME:GDSIIStruct",
       "ImportStruct:=", True,
       "CreateNewCell:=", True,
       "StructName:=", "SIM1"
       ]
      ]
     ])

# Create 3D geometry
import_bounding_box = oEditor.GetModelBoundingBox()
objects = {}
pec_sheets = []
for i, face in enumerate(face_stack):
    if not face:
        continue

    # Get lists of imported objects (2d sheets)
    objects[face] = {n: oEditor.GetMatchedObjectName(face + '_' + n + '_*') for n in layer_names}

    # Move all sheets to correct z-level
    sign = (-1) ** (i + int(lower_box_height > 0))
    face_objects = [o for n in layer_names if n != 'airbridge_flyover' for o in objects[face][n]]
    move_vertically(oEditor, face_objects, z_levels[i + 1], units)
    move_vertically(oEditor, objects[face]['airbridge_flyover'], z_levels[i + 1] + sign * airbridge_height, units)

    # Thicken airbridge pads, indium bumps, and TSVs
    thicken_sheet(oEditor, objects[face]['airbridge_pads'], sign * airbridge_height, units, "sc_metal")
    signed_vacuum_thickness = z_levels[i + 1 + sign] - z_levels[i + 1]
    thicken_sheet(oEditor, objects[face]['indium_bump'], signed_vacuum_thickness, units, "sc_metal")
    signed_substrate_thickness = z_levels[i + 1 - sign] - z_levels[i + 1]
    if hollow_tsv:
        edges = objects_from_sheet_edges(oEditor, objects[face]['tsv'])
        thicken_sheet(oEditor, edges, signed_substrate_thickness, units)
        pec_sheets += edges
        thicken_sheet(oEditor, objects[face]['tsv'], signed_substrate_thickness, units, "vacuum", True)
    else:
        thicken_sheet(oEditor, objects[face]['tsv'], signed_substrate_thickness, units, "sc_metal")

# Assign perfect electric conductor to imported objects
pec_sheets += [o for f in face_stack if f for n in ['signal', 'ground', 'airbridge_flyover'] for o in objects[f][n]]
if ansys_tool in {'hfss', 'eigenmode'}:
    oBoundarySetup.AssignPerfectE(
        ["NAME:PerfE1",
         "Objects:=", pec_sheets,
         "InfGroundPlane:=", False
         ])
elif ansys_tool == 'q3d':
    oBoundarySetup.AssignThinConductor(
        [
            "NAME:ThinCond1",
            "Objects:=", pec_sheets,
            "Material:=", "pec",
            "Thickness:=", "1nm"  # thickness does not matter when material is pec
        ])

# Create ports or nets
signal_objects = [o for f in face_stack if f for o in objects[f]['signal']]
ground_objects = [o for f in face_stack if f for o in objects[f]['ground']]
if ansys_tool in {'hfss', 'eigenmode'}:
    ports = sorted(data['ports'], key=lambda k: k['number'])
    for port in ports:
        is_wave_port = port['type'] == 'EdgePort'
        if not is_wave_port or not use_ansys_project_template:
            if 'polygon' not in port:
                continue

            polyname = 'Port%d' % port['number']

            # Create polygon spanning the two edges
            create_polygon(oEditor, polyname,
                           [list(p) for p in port['polygon']], units)

            oBoundarySetup.AutoIdentifyPorts(
                ["NAME:Faces", int(oEditor.GetFaceIDs(polyname)[0])],
                is_wave_port,
                ["NAME:ReferenceConductors"] + ground_objects,
                str(port['number']),
                False)

            if ("deembed_len" in port) and (port["deembed_len"] is not None):
                oBoundarySetup.EditWavePort(
                    str(port['number']),
                    ["Name:%d" % port['number'],
                     "DoDeembed:=", True,
                     "DeembedDist:=", "%f%s" % (port["deembed_len"], units)
                     ]
                )

            # Turn junctions to lumped RLC
            if port['junction'] and ansys_tool == 'eigenmode':
                # add junction inductance variable
                oDesign.ChangeProperty(
                    ["NAME:AllTabs",
                        ["NAME:LocalVariableTab",
                            ["NAME:PropServers", "LocalVariables"],
                            ["NAME:NewProps",
                                ["NAME:Lj_%d" % port['number'],
                                 "PropType:=", "VariableProp",
                                 "UserDef:=", True,
                                 "Value:=", "%.32eH" % port['inductance']]  # use best float precision
                            ]
                        ]
                    ])
                # add junction capacitance variable
                oDesign.ChangeProperty(
                    ["NAME:AllTabs",
                        ["NAME:LocalVariableTab",
                            ["NAME:PropServers", "LocalVariables"],
                            ["NAME:NewProps",
                                ["NAME:Cj_%d" % port['number'],
                                 "PropType:=", "VariableProp",
                                 "UserDef:=", True,
                                 "Value:=", "%.32efarad" % port['capacitance']]
                            ]
                        ]
                    ])

                current_start = ["%.32e%s" % (p, units) for p in port['signal_location']]
                current_end = ["%.32e%s" % (p, units) for p in port['ground_location']]

                oDesign.GetModule("BoundarySetup").AssignLumpedRLC(
                    ["NAME:LumpRLC_jj_%d" % port['number'],
                     "Objects:=", [polyname],
                        ["NAME:CurrentLine",  # set direction of current across junction
                         "Coordinate System:=", "Global",
                         "Start:=", current_start,
                         "End:=", current_end],
                     "RLC Type:=", "Parallel",
                     "UseResist:=", False,
                     "UseInduct:=", True,
                     "Inductance:=", "Lj_%d" % port['number'],
                     "UseCap:=", True,
                     "Capacitance:=", "Cj_%d" % port['number'],
                     "Faces:=", [int(oEditor.GetFaceIDs(polyname)[0])]
                    ])

                if 'pyepr' in simulation_flags:
                    # add polyline across junction for voltage across the junction
                    oEditor.CreatePolyline(
                        ["NAME:PolylineParameters",
                        "IsPolylineCovered:=", True,
                        "IsPolylineClosed:=", False,
                            ["NAME:PolylinePoints",
                            ["NAME:PLPoint",
                            "X:=", current_start[0],
                            "Y:=", current_start[1],
                            "Z:=", current_start[2]],
                            ["NAME:PLPoint",
                            "X:=", current_end[0],
                            "Y:=", current_end[1],
                            "Z:=", current_end[2]]],
                            ["NAME:PolylineSegments",
                            ["NAME:PLSegment",
                            "SegmentType:=", "Line",
                            "StartIndex:=", 0,
                            "NoOfPoints:=", 2]],
                            ["NAME:PolylineXSection",
                            "XSectionType:=", "None",
                            "XSectionOrient:=", "Auto",
                            "XSectionWidth:=", "0" + units,
                            "XSectionTopWidth:=", "0" + units,
                            "XSectionHeight:=", "0" + units,
                            "XSectionNumSegments:=", "0",
                            "XSectionBendType:=", "Corner"]],
                        ["NAME:Attributes",
                        "Name:=", "Junction%d" % port['number'],
                        "Flags:=", "",
                        "Color:=", "(143 175 143)",
                        "Transparency:=", 0.4,
                        "PartCoordinateSystem:=", "Global",
                        "UDMId:=", "",
                        "MaterialValue:=", "\"vacuum\"",
                        "SurfaceMaterialValue:=", "\"\"",
                        "SolveInside:=", True,
                        "ShellElement:=", False,
                        "ShellElementThickness:=", "0" + units,
                        "IsMaterialEditable:="	, True,
                        "UseMaterialAppearance:=", False,
                        "IsLightweight:="	, False
                        ])

                    oEditor.ChangeProperty(
                        ["NAME:AllTabs",
                            ["NAME:Geometry3DAttributeTab",
                                ["NAME:PropServers", "Junction%d" % port['number']],
                                ["NAME:ChangedProps",
                                    ["NAME:Show Direction",
                                    "Value:=", True]]]
                        ])

    if ansys_tool == 'eigenmode':
        oBoundarySetup.DeleteAllExcitations()


elif ansys_tool == 'q3d':
    port_objects = []  # signal objects to be assigned as SignalNets
    ports = sorted(data['ports'], key=lambda k: k['number'])
    for port in ports:
        signal_location = port['signal_location']
        if 'ground_location' in port:
            # Use 1e-2 safe margin to ensure that signal_location is inside the signal polygon:
            signal_location = [x + 1e-2 * (x - y) for x, y in zip(signal_location, port['ground_location'])]
        port_object = oEditor.GetBodyNamesByPosition(
            ["NAME:Parameters",
             "XPosition:=", str(signal_location[0]) + units,
             "YPosition:=", str(signal_location[1]) + units,
             "ZPosition:=", str(signal_location[2]) + units
             ])

        if len(port_object) == 1 and port_object[0] not in port_objects and port_object[0] in signal_objects:
            port_objects.append(port_object[0])

    if not port_objects:
        port_objects = signal_objects  # port_objects is empty -> assign all signals as SignalNets without sorting

    for i, signal_object in enumerate(port_objects):
        oBoundarySetup.AssignSignalNet(
            ["NAME:Net{}".format(i + 1),
             "Objects:=", [signal_object]
             ])
    for i, floating_object in enumerate([obj for obj in signal_objects if obj not in port_objects]):
        oBoundarySetup.AssignFloatingNet(
            ["NAME:Floating{}".format(i + 1),
             "Objects:=", [floating_object]
             ])
    for i, ground_object in enumerate(ground_objects):
        oBoundarySetup.AssignGroundNet(
            ["NAME:Ground{}".format(i + 1),
             "Objects:=", [ground_object]
             ])
    oBoundarySetup.AutoIdentifyNets()  # Combine Nets by conductor connections. Order: GroundNet, SignalNet, FloatingNet


# Create (floating) sheets modelling participation surfaces
if participation_sheet_distance is not None:
    for layer, src_names, side, height in (
            ('layerMA', ['signal', 'ground'], 1, 0),  # metal-air (vacuum)
            ('layerMS', ['signal', 'ground'], -1, 0),  # metal-substrate
            ('layerSA', ['gap'], 1, -vertical_over_etching),  # substrate-air (vacuum)
    ):
        layer_objs = []
        for i, face in enumerate(face_stack):
            if not face:
                continue

            sign = (-1) ** (i + int(lower_box_height > 0))
            objs = [o for n in src_names for o in objects[face][n]]
            if not objs:  # skip if no objects given
                continue

            # duplicate objs and transform
            objs_copy = copy_paste(oEditor, objs)
            move_vertically(oEditor, objs_copy, sign * (side * participation_sheet_distance + height), units)
            if thicken_participation_sheet_distance:
                thicken_sheet(oEditor, objs_copy, sign * side * thicken_participation_sheet_distance, units)
            layer_objs += objs_copy

        # combine objects to just `layer`
        if len(layer_objs) > 1:  # unite fails for only one selected object
            oEditor.Unite(
                ["NAME:Selections", "Selections:=", ','.join(layer_objs)],
                ["NAME:UniteParameters", "KeepOriginals:=", False]
            )
        oEditor.ChangeProperty(
            ["NAME:AllTabs",
             ["NAME:Geometry3DAttributeTab",
              ["NAME:PropServers", layer_objs[0]],
              ["NAME:ChangedProps",
               ["NAME:Model", "Value:=", False],  # non-modelled sheet
               ["NAME:Color", "R:=", 197, "G:=", 197, "B:=", 197],  # grey
               ["NAME:Name", "Value:=", layer]
               ]
              ]
             ])

if not use_ansys_project_template:
    # Create substrate and vacuum boxes
    import_bounding_box = oEditor.GetModelBoundingBox()

    for i in range(len(z_levels) - 1):
        is_vacuum = bool((i + int(lower_box_height > 0)) % 2)
        box_name = "Vacuum" if is_vacuum else "Substrate"
        create_box(
            oEditor, box_name if i < 2 else '{}_{}'.format(box_name, i // 2),
            float(import_bounding_box[0]), float(import_bounding_box[1]), z_levels[i],
            float(import_bounding_box[3]) - float(import_bounding_box[0]),
            float(import_bounding_box[4]) - float(import_bounding_box[1]),
            z_levels[i + 1] - z_levels[i],
            "vacuum" if is_vacuum else "si",
            units)

    # Insert analysis setup
    setup = data['analysis_setup']

    if ansys_tool == 'hfss':
        # create setup_list for analysis setup with TWO OPTIONS: multiple frequency or single frequency
        multiple_frequency = (isinstance(setup['frequency'], list))
        setup_list = [
            "NAME:Setup1",
            "AdaptMultipleFreqs:=", multiple_frequency
        ]

        if multiple_frequency:
            max_delta_s = setup['max_delta_s']
            if not isinstance(type(max_delta_s), list):
                max_delta_s = [max_delta_s] * len(setup['frequency'])  # make max_delta_s a list
            maf_setup_list = ["NAME:MultipleAdaptiveFreqsSetup"]
            for f, s in zip(setup['frequency'], max_delta_s):
                maf_setup_list += [str(f) + setup['frequency_units'] + ":=", [s]]
            setup_list += [maf_setup_list]
        else:
            setup_list += [
                "Frequency:=", str(setup['frequency']) + setup['frequency_units'],
                "MaxDeltaS:=", setup['max_delta_s']
            ]

        setup_list += [
            "MaximumPasses:=", setup['maximum_passes'],
            "MinimumPasses:=", setup['minimum_passes'],
            "MinimumConvergedPasses:=", setup['minimum_converged_passes'],
            "PercentRefinement:=", setup['percent_refinement'],
            "IsEnabled:=", True,
            ["NAME:MeshLink",
             "ImportMesh:=", False
             ],
            "BasisOrder:=", 1,
            "DoLambdaRefine:=", True,
            "DoMaterialLambda:=", True,
            "SetLambdaTarget:=", False,
            "Target:=", 0.3333,
            "UseMaxTetIncrease:=", False,
            "PortAccuracy:=", 0.2,
            "UseABCOnPort:=", False,
            "SetPortMinMaxTri:=", False,
            "UseDomains:=", False,
            "UseIterativeSolver:=", False,
            "SaveRadFieldsOnly:=", False,
            "SaveAnyFields:=", True,
            "IESolverType:=", "Auto",
            "LambdaTargetForIESolver:=", 0.15,
            "UseDefaultLambdaTgtForIESolver:=", True
        ]
        oAnalysisSetup.InsertSetup("HfssDriven", setup_list)


        oAnalysisSetup.InsertFrequencySweep(
            "Setup1",
            ["NAME:Sweep",
             "IsEnabled:=", setup['sweep_enabled'],
             "RangeType:=", "LinearCount",
             "RangeStart:=", str(setup['sweep_start']) + setup['frequency_units'],
             "RangeEnd:=", str(setup['sweep_end']) + setup['frequency_units'],
             "RangeCount:=", setup['sweep_count'],
             "Type:=", setup['sweep_type'],
             "SaveFields:=", False,
             "SaveRadFields:=", False,
             "InterpTolerance:=", 0.5,
             "InterpMaxSolns:=", 250,
             "InterpMinSolns:=", 0,
             "InterpMinSubranges:=", 1,
             "ExtrapToDC:=", setup['sweep_start'] == 0,
             "MinSolvedFreq:=", "0.01GHz",
             "InterpUseS:=", True,
             "InterpUsePortImped:=", True,
             "InterpUsePropConst:=", True,
             "UseDerivativeConvergence:=", False,
             "InterpDerivTolerance:=", 0.2,
             "UseFullBasis:=", True,
             "EnforcePassivity:=", True,
             "PassivityErrorTolerance:=", 0.0001,
             "EnforceCausality:=", False
             ])
    elif ansys_tool == 'q3d':
        if isinstance(type(setup['frequency']), list):
            setup['frequency'] = setup['frequency'][0]
            oDesktop.AddMessage("", "", 0, "Multi-frequency is not supported in Q3D. Create setup with frequency "
                                           "{}.".format(str(setup['frequency']) + setup['frequency_units']))

        oAnalysisSetup.InsertSetup("Matrix",
                                   [
                                       "NAME:Setup1",
                                       "AdaptiveFreq:=", str(setup['frequency']) + setup['frequency_units'],
                                       "SaveFields:=", False,
                                       "Enabled:=", True,
                                       [
                                           "NAME:Cap",
                                           "MaxPass:=", setup['maximum_passes'],
                                           "MinPass:=", setup['minimum_passes'],
                                           "MinConvPass:=", setup['minimum_converged_passes'],
                                           "PerError:=", setup['percent_error'],
                                           "PerRefine:=", setup['percent_refinement'],
                                           "AutoIncreaseSolutionOrder:=", True,
                                           "SolutionOrder:=", "High",
                                           "Solver Type:=", "Iterative"
                                       ]
                                   ])
    elif ansys_tool == 'eigenmode':
        # Create EM setup
        min_freq_ghz = str(setup.get('frequency', 0.1)) + setup['frequency_units']

        setup_list = [
            "NAME:Setup1",
            "MinimumFrequency:=", min_freq_ghz,
            "NumModes:=", setup['n_modes'],
            "MaxDeltaFreq:=", setup['max_delta_f'],
            "ConvergeOnRealFreq:=", True,
            "MaximumPasses:=", setup['maximum_passes'],
            "MinimumPasses:=", setup['minimum_passes'],
            "MinimumConvergedPasses:=", setup['minimum_converged_passes'],
            "PercentRefinement:=", setup['percent_refinement'],
            "IsEnabled:=", True,
            "BasisOrder:=", 1
        ]
        oAnalysisSetup.InsertSetup("HfssEigen", setup_list)

else:
    scriptpath = os.path.dirname(__file__)
    aedt_path = os.path.join(scriptpath, '../')
    basename = os.path.splitext(os.path.basename(jsonfile))[0]
    build_geom_name = basename + "_build_geometry"
    template_path = data['ansys_project_template']
    template_basename = os.path.splitext(os.path.basename(template_path))[0]

    oProject = oDesktop.GetActiveProject()
    oProject.SaveAs(os.path.join(aedt_path, build_geom_name + ".aedt"), True)

    oDesign = oProject.GetActiveDesign()
    oEditor = oDesign.SetActiveEditor("3D Modeler")
    sheet_name_list = oEditor.GetObjectsInGroup('Sheets') + oEditor.GetObjectsInGroup('Solids')
    oEditor.Copy(
        [
            "NAME:Selections",
            "Selections:="		, ",".join(sheet_name_list)
        ])

    oDesktop.OpenProject(os.path.join(aedt_path, template_path))
    oProject = oDesktop.SetActiveProject(template_basename)
    oDesign = oProject.SetActiveDesign("HFSSDesign1")
    oEditor = oDesign.SetActiveEditor("3D Modeler")
    oEditor.Paste()
    oDesktop.CloseProject(build_geom_name)

if vertical_over_etching > 0:
    # In case of vertical over-etching, solids of vacuum are created inside substrates (overrides substrate material).
    # Solve Inside parameter must be set in 'hfss' and 'eigenmode' simulations to avoid warnings.
    # Solve Inside doesn't exists in 'q3d', so we use None in thicken_sheet function to ignore the parameter.
    solve_inside = True if ansys_tool in ['hfss', 'eigenmode'] else None
    for i, face in enumerate(face_stack):
        if not face:
            continue

        sign = (-1) ** (i + int(lower_box_height > 0))
        gap_objects = objects[face]['gap']
        thicken_sheet(oEditor, gap_objects, -sign * vertical_over_etching, units, "vacuum", solve_inside)

if gap_max_element_length is not None:
    # Manual mesh refinement on gap sheets (or solids in case of vertical over-etching)
    gap_objects = [o for f in face_stack if f for o in objects[f]['gap']]
    oMeshSetup = oDesign.GetModule("MeshSetup")
    oMeshSetup.AssignLengthOp(
            [
                "NAME:GapLength",
                "RefineInside:=", False,
                "Enabled:=", True,
                "Objects:=", gap_objects,
                "RestrictElem:=", False,
                # "NumMaxElem:=", 100000
                "RestrictLength:=", True,
                "MaxLength:=", str(gap_max_element_length) + units
            ])

# Fit window to objects
oEditor.FitAll()

# Notify the end of script
oDesktop.AddMessage("", "", 0, "Import completed (%s)" % time.asctime(time.localtime()))
