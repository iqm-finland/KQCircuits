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
from geometry import create_box, create_polygon  # pylint: disable=wrong-import-position

# Set up environment
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.AddMessage("", "", 0, "Starting import script (%s)" % time.asctime(time.localtime()))

# Import metadata (bounding box and port information)
jsonfile = ScriptArgument
path = os.path.dirname(jsonfile)

with open(jsonfile, 'r') as fjsonfile:
    data = json.load(fjsonfile)

ansys_tool = data['ansys_tool'] if 'ansys_tool' in data else 'hfss'
gds_file = data['gds_file']
signal_layer = data['signal_layer']
ground_layer = data['ground_layer']
substrate_height = data['substrate_height']
airbridge_height = data['airbridge_height'] if 'airbridge_height' in data else 0
box_height = data['box_height']
permittivity = data['permittivity']
units = data['units']
wafer_stack_type = data['stack_type']
vacuum_box_height = box_height
layer_map_option = []
entry_option = []

if wafer_stack_type == "multiface":
    substrate_height_top = data['substrate_height_top']
    chip_distance = data['chip_distance']
    t_signal_layer = data['t_signal_layer']
    t_ground_layer = data['t_ground_layer']
    layer_map_option = [["NAME:LayerMapInfo",
                         "LayerNum:=", t_signal_layer,
                         "DestLayer:=", "t_Signal",
                         "layer_type:=", "signal"
                         ],
                        ["NAME:LayerMapInfo",
                         "LayerNum:=", t_ground_layer,
                         "DestLayer:=", "t_Ground",
                         "layer_type:=", "signal"
                         ]]
    entry_option = [
        "entry:=", ["order:=", 2, "layer:=", "t_Signal"],
        "entry:=", ["order:=", 3, "layer:=", "t_Ground"]]
    vacuum_box_height = chip_distance
    if 'b_bump_layer' in data:
        entry_option += [
            "entry:=", ["order:=", 4, "layer:=", "b_Indium_Bumps"],
            "entry:=", ["order:=", 5, "layer:=", "t_Indium_Bumps"]]
        layer_map_option += [["NAME:LayerMapInfo",
                              "LayerNum:=", data['b_bump_layer'],
                              "DestLayer:=", "b_Indium_Bumps",
                              "layer_type:=", "signal"
                              ],
                             ["NAME:LayerMapInfo",
                              "LayerNum:=", data['t_bump_layer'],
                              "DestLayer:=", "t_Indium_Bumps",
                              "layer_type:=", "signal"
                              ]]

if 'airbridge_pads_layer' in data:
    entry_option += [
        "entry:=", ["order:=", 6, "layer:=", "Airbridge_Flyover"],
        "entry:=", ["order:=", 7, "layer:=", "Airbridge_Pads"]]
    layer_map_option += [["NAME:LayerMapInfo",
                          "LayerNum:=", data['airbridge_flyover_layer'],
                          "DestLayer:=", "Airbridge_Flyover",
                          "layer_type:=", "signal"
                          ],
                         ["NAME:LayerMapInfo",
                          "LayerNum:=", data['airbridge_pads_layer'],
                          "DestLayer:=", "Airbridge_Pads",
                          "layer_type:=", "signal"
                          ]]

# Create project
oDesktop.RestoreWindow()
oProject = oDesktop.NewProject()
oDefinitionManager = oProject.GetDefinitionManager()

if ansys_tool == 'hfss':
    oProject.InsertDesign("HFSS", "HFSSDesign1", "DrivenTerminal", "")
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
     "permittivity:=", str(permittivity)
     ])
oDefinitionManager.AddMaterial(
    ["NAME:sc_metal",
     "CoordinateSystemType:=", "Cartesian",
     "BulkOrSurfaceType:=", 1,
     ["NAME:PhysicsTypes", "set:=", ["Electromagnetic"]],
     "conductivity:=", "1e+30"
     ])

# Import GDSII geometry
order_map = ["entry:=", ["order:=", 0, "layer:=", "Signal"],
             "entry:=", ["order:=", 1, "layer:=", "Ground"],
             ] + entry_option

layer_map = ["NAME:LayerMap",
             ["NAME:LayerMapInfo",
              "LayerNum:=", signal_layer,
              "DestLayer:=", "Signal",
              "layer_type:=", "signal"
              ],
             ["NAME:LayerMapInfo",
              "LayerNum:=", ground_layer,
              "DestLayer:=", "Ground",
              "layer_type:=", "signal"
              ],
             ] + layer_map_option

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

# Get lists of imported objects (= 2D chip geometry)
signal_objects = oEditor.GetMatchedObjectName('Signal_*')  # all signal objects (also t_signal_objects from top-chip)
ground_objects = oEditor.GetMatchedObjectName('Ground_*')  # all ground objects (also t_ground_objects from top-chip)
airbridge_pads_objects = oEditor.GetMatchedObjectName('Airbridge_Pads_*')
airbridge_flyover_objects = oEditor.GetMatchedObjectName('Airbridge_Flyover_*')

# Assign perfect electric conductor to imported objects
if ansys_tool == 'hfss':
    oBoundarySetup.AssignPerfectE(
        ["NAME:PerfE1",
         "Objects:=", signal_objects + ground_objects + airbridge_flyover_objects,
         "InfGroundPlane:=", False
         ])
elif ansys_tool == 'q3d':
    oBoundarySetup.AssignThinConductor(
        [
            "NAME:ThinCond1",
            "Objects:=", signal_objects + ground_objects + airbridge_flyover_objects,
            "Material:=", "pec",
            "Thickness:=", "1nm"  # thickness does not matter when material is pec
        ])

if wafer_stack_type == 'multiface':
    # move all top-chip elements to the top face
    top_objects = oEditor.GetMatchedObjectName('t_*')
    for selection in top_objects:
        oEditor.Move(["NAME:Selections", "Selections:=", selection],
                     ["NAME:TranslateParameters",
                      "TranslateVectorX:=", "0 um",
                      "TranslateVectorY:=", "0 um",
                      "TranslateVectorZ:=", "{} {}".format(chip_distance, units)])

    # Assign metalization
    t_signal_objects = oEditor.GetMatchedObjectName('t_Signal_*')
    t_ground_objects = oEditor.GetMatchedObjectName('t_Ground_*')
    signal_objects += t_signal_objects
    ground_objects += t_ground_objects
    if ansys_tool == 'hfss':
        oBoundarySetup.AssignPerfectE(
            ["NAME:PerfE2",
             "Objects:=", t_ground_objects + t_signal_objects,
             "InfGroundPlane:=", False
             ])
    elif ansys_tool == 'q3d':
        oBoundarySetup.AssignThinConductor(
            ["NAME:ThinCond2",
             "Objects:=", t_ground_objects + t_signal_objects,
             "Material:=", "pec",
             "Thickness:=", "1nm"  # thickness does not matter when material is pec
             ])

    # Indium bumps
    t_bump_objects = oEditor.GetMatchedObjectName('t_Indium_Bumps_*')
    b_bump_objects = oEditor.GetMatchedObjectName('b_Indium_Bumps_*')

    if b_bump_objects:
        oEditor.SweepAlongVector(
            ["NAME:Selections",
             "Selections:=", ",".join(b_bump_objects),
             "NewPartsModelFlag:=", "Model"],
            ["NAME:VectorSweepParameters",
             "DraftAngle:=", "0deg",
             "DraftType:=", "Round",
             "CheckFaceFaceIntersection:=", False,
             "SweepVectorX:=", "0um",
             "SweepVectorY:=", "0um",
             "SweepVectorZ:=", "{} {}".format(chip_distance / 2, units)
             ])
        oEditor.ChangeProperty(
            ["NAME:AllTabs",
             ["NAME:Geometry3DAttributeTab",
              ["NAME:PropServers"] + b_bump_objects,
              ["NAME:ChangedProps",
               ["NAME:Material", "Value:=", "\"sc_metal\""]
               ]
              ]
             ])

    if t_bump_objects:
        oEditor.SweepAlongVector(
            ["NAME:Selections",
             "Selections:=", ",".join(t_bump_objects),
             "NewPartsModelFlag:=", "Model"],
            ["NAME:VectorSweepParameters",
             "DraftAngle:=", "0deg",
             "DraftType:=", "Round",
             "CheckFaceFaceIntersection:=", False,
             "SweepVectorX:=", "0um",
             "SweepVectorY:=", "0um",
             "SweepVectorZ:=", "{} {}".format(-chip_distance / 2, units)
             ])
        oEditor.ChangeProperty(
            ["NAME:AllTabs",
             ["NAME:Geometry3DAttributeTab",
              ["NAME:PropServers"] + t_bump_objects,
              ["NAME:ChangedProps",
               ["NAME:Material", "Value:=", "\"sc_metal\""]
               ]
              ]
             ])

# Process airbridge geometry
if airbridge_pads_objects:
    oEditor.SweepAlongVector(
        ["NAME:Selections",
         "Selections:=", ",".join(airbridge_pads_objects),
         "NewPartsModelFlag:=", "Model"],
        ["NAME:VectorSweepParameters",
         "DraftAngle:=", "0deg",
         "DraftType:=", "Round",
         "CheckFaceFaceIntersection:=", False,
         "SweepVectorX:=", "0um",
         "SweepVectorY:=", "0um",
         "SweepVectorZ:=", "{} {}".format(airbridge_height, units)
         ])
    oEditor.ChangeProperty(
        ["NAME:AllTabs",
         ["NAME:Geometry3DAttributeTab",
          ["NAME:PropServers"] + airbridge_pads_objects,
          ["NAME:ChangedProps",
           ["NAME:Material", "Value:=", "\"sc_metal\""]
           ]
          ]
         ])

if airbridge_flyover_objects:
    oEditor.Move(
        ["NAME:Selections",
         "Selections:=", ",".join(airbridge_flyover_objects),
         "NewPartsModelFlag:=", "Model"
         ],
        ["NAME:TranslateParameters",
         "TranslateVectorX:=", "0um",
         "TranslateVectorY:=", "0um",
         "TranslateVectorZ:=", "{} {}".format(airbridge_height, units)
         ])

# Create ports or nets
if ansys_tool == 'hfss':
    ports = sorted(data['ports'], key=lambda k: k['number'])
    for port in ports:
        polyname = 'Port%d' % port['number']

        # Create polygon spanning the two edges
        create_polygon(oEditor, polyname,
                       [list(p) for p in port['polygon']], units)

        is_wave_port = port['type'] == 'EdgePort'

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

elif ansys_tool == 'q3d':
    port_objects = []  # signal objects to be assigned as SignalNets
    ports = sorted(data['ports'], key=lambda k: k['number'])
    for port in ports:
        # Compute the signal location of the port
        if 'ground_location' in port:
            # Use 1e-2 safe margin to ensure that signal_location is in the signal polygon:
            signal_location = [x + 1e-2 * (x - y) for x, y in zip(port['signal_location'], port['ground_location'])]
        else:
            signal_location = list(port['signal_location'])
        signal_location += [chip_distance if port['face'] == 1 else 0.0]  # z-component

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

# Create substrate and vacuum boxes
import_bounding_box = oEditor.GetModelBoundingBox()

create_box(
    oEditor, "Box",
    float(import_bounding_box[0]), float(import_bounding_box[1]), 0,
    float(import_bounding_box[3]) - float(import_bounding_box[0]),
    float(import_bounding_box[4]) - float(import_bounding_box[1]),
    vacuum_box_height,
    "vacuum",
    units)

create_box(
    oEditor, "Substrate",
    float(import_bounding_box[0]), float(import_bounding_box[1]), 0,
    float(import_bounding_box[3]) - float(import_bounding_box[0]),
    float(import_bounding_box[4]) - float(import_bounding_box[1]),
    -substrate_height,
    "si",
    units)

if wafer_stack_type == 'multiface':
    create_box(
        oEditor, "Top_chip",
        float(import_bounding_box[0]), float(import_bounding_box[1]), chip_distance,
        float(import_bounding_box[3]) - float(import_bounding_box[0]),
        float(import_bounding_box[4]) - float(import_bounding_box[1]),
        substrate_height_top,
        "si",
        units)

# Fit window to objects
oEditor.FitAll()

# Insert analysis setup
if 'analysis_setup' in data:
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
             "Type:=", "Interpolating",
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

# Notify the end of script
oDesktop.AddMessage("", "", 0, "Import completed (%s)" % time.asctime(time.localtime()))
