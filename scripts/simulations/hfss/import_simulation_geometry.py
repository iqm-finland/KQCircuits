# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy's prior
# written permission.

# This is a Python 2.7 script that should be run in HFSS in order to import and run the simulation
import time
import os
import sys
import json
import ScriptEnv


## Aux function
def get_boundary_face(label, value, above=True):
    if above:
        boundary_face = [int(f) for f in oEditor.GetFaceIDs(label)
                         if float(oEditor.GetFaceCenter(f)[2]) > value]
    else:
        boundary_face = [int(f) for f in oEditor.GetFaceIDs(label)
                         if float(oEditor.GetFaceCenter(f)[2]) < value]
    return boundary_face


## TODO: Figure out how to set the python path for the HFSS internal IronPython
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'util'))
from geometry import create_box, create_polygon

# Set up environment
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")

oDesktop.AddMessage("", "", 0, "Starting import script (%s)" % time.asctime(time.localtime()))

jsonfile = ScriptArgument
path = os.path.dirname(jsonfile)
basename = os.path.splitext(os.path.basename(jsonfile))[0]

## Import metadata (bounding box and port information)
fjsonfile = open(jsonfile, 'r')
data = json.load(fjsonfile)
fjsonfile.close()

## CREATE PROJECT
oDesktop.RestoreWindow()
oProject = oDesktop.NewProject()
oDefinitionManager = oProject.GetDefinitionManager()

oProject.InsertDesign("HFSS", "HFSSDesign1", "DrivenTerminal", "")
oDesign = oProject.SetActiveDesign("HFSSDesign1")
oEditor = oDesign.SetActiveEditor("3D Modeler")
oBoundarySetup = oDesign.GetModule("BoundarySetup")
oAnalysisSetup = oDesign.GetModule("AnalysisSetup")
oOutputVariable = oDesign.GetModule("OutputVariable")
oSolutions = oDesign.GetModule("Solutions")
oReportSetup = oDesign.GetModule("ReportSetup")

## Simulation parameters, defined in klayout
gds_file = data['gds_file']
signal_layer = data['signal_layer']
ground_layer = data['ground_layer']
substrate_height = data['substrate_height']
airbridge_height = data['airbridge_height'] if 'airbridge_height' in data else 0
box_height = data['box_height']
epsilon = data['epsilon']
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

if 'airbridge_pads_layer' in data:
    entry_option += [
        "entry:=", ["order:=", 4, "layer:=", "Airbridge_Flyover"],
        "entry:=", ["order:=", 5, "layer:=", "Airbridge_Pads"]]
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

## Set HFSS units
oEditor.SetModelUnits(['NAME:Units Parameter', 'Units:=', units, 'Rescale:=', False])

## MATERIALS
oDefinitionManager.AddMaterial(
    ["NAME:si",
     "CoordinateSystemType:=", "Cartesian",
     "BulkOrSurfaceType:=", 1,
     ["NAME:PhysicsTypes", "set:=", ["Electromagnetic"]],
     "permittivity:=", str(epsilon)
     ])
oDefinitionManager.AddMaterial(
    ["NAME:sc_al",
     "CoordinateSystemType:=", "Cartesian",
     "BulkOrSurfaceType:=", 1,
     ["NAME:PhysicsTypes", "set:=", ["Electromagnetic"]],
     "conductivity:="	, "inf "
     ])

## IMPORT GDSII geometry
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

# WORKAROUND: For unknown reason, HFSS 2020R1 performs the import twice. Delete second one if we find it
imported_objects = oEditor.GetSelections()
all_objects = oEditor.GetMatchedObjectName('*')
if len(all_objects) > len(imported_objects):
    oEditor.Delete(
        [
            "NAME:Selections",
            "Selections:=", ",".join(imported_objects)
        ])

# Get list of imported objects (= 2D chip geometry)
signal_objects = oEditor.GetMatchedObjectName('Signal_*')
ground_objects = oEditor.GetMatchedObjectName('Ground_*')
airbridge_pads_objects = oEditor.GetMatchedObjectName('Airbridge_Pads_*')
airbridge_flyover_objects = oEditor.GetMatchedObjectName('Airbridge_Flyover_*')

# Get bounding box
import_bounding_box = oEditor.GetModelBoundingBox()

# Assign perfect E boundary to imported objects
oBoundarySetup.AssignPerfectE(
    ["NAME:PerfE1",
     "Objects:=", signal_objects + ground_objects + airbridge_flyover_objects,
     "InfGroundPlane:=", False
     ])

## CREATE PORTS
for port in data['ports']:
    polyname = 'Port%d' % port['number']

    # Create polygon spanning the two edges
    create_polygon(oEditor, polyname,
                   [[x for x in p] for p in port['polygon']], units)

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

# Create substrate
create_box(
    oEditor, "Substrate",
    float(import_bounding_box[0]), float(import_bounding_box[1]), 0,
    float(import_bounding_box[3]) - float(import_bounding_box[0]),
    float(import_bounding_box[4]) - float(import_bounding_box[1]),
    -substrate_height,
    "si",
    units)

# Get substrate faces except the internal one at z=0 (external boundaries)
substrateboundaryfaces = get_boundary_face("Substrate", 0, False)

# Create vacuum box
create_box(
    oEditor, "Box",
    float(import_bounding_box[0]), float(import_bounding_box[1]), 0,
    float(import_bounding_box[3]) - float(import_bounding_box[0]),
    float(import_bounding_box[4]) - float(import_bounding_box[1]),
    vacuum_box_height,
    "vacuum",
    units)

# Get box faces except the internal one at z=0 (external boundaries)
boxboundaryfaces = get_boundary_face("Box", 0)

external_boundary = boxboundaryfaces + substrateboundaryfaces

if wafer_stack_type == 'multiface':

    create_box(
        oEditor, "Top_chip",
        float(import_bounding_box[0]), float(import_bounding_box[1]), chip_distance,
        float(import_bounding_box[3]) - float(import_bounding_box[0]),
        float(import_bounding_box[4]) - float(import_bounding_box[1]),
        substrate_height_top,
        "si",
        units)

    # Get box faces except the internal one at z=0 (external boundaries)
    topchipboundaryfaces = get_boundary_face("Top_chip", chip_distance, True)
    external_boundary += topchipboundaryfaces

    # move all top-chip elements to the top face
    top_objects = oEditor.GetMatchedObjectName('t_*')
    for selection in top_objects:
        oEditor.Move(["NAME:Selections", "Selections:=", selection],
                     ["NAME:TranslateParameters",
                      "TranslateVectorX:=", "0 um",
                      "TranslateVectorY:=", "0 um",
                      "TranslateVectorZ:=", "{} {}".format(chip_distance, units)])

    top_ground = oEditor.GetMatchedObjectName('t_Ground*')
    oBoundarySetup.AssignPerfectE(
        ["NAME:PerfE3",
         "Objects:=", top_ground,
         "InfGroundPlane:=", False
         ])

# Process airbridge geometry
if airbridge_pads_objects:
    oEditor.SweepAlongVector(
        ["NAME:Selections",
         "Selections:="		, ",".join(airbridge_pads_objects),
         "NewPartsModelFlag:="	, "Model"],
        ["NAME:VectorSweepParameters",
         "DraftAngle:="		, "0deg",
         "DraftType:="		, "Round",
         "CheckFaceFaceIntersection:=", False,
         "SweepVectorX:="	, "0um",
         "SweepVectorY:="	, "0um",
         "SweepVectorZ:="	, "{} {}".format(airbridge_height, units)
         ])
    oEditor.ChangeProperty(
        ["NAME:AllTabs",
         ["NAME:Geometry3DAttributeTab",
          ["NAME:PropServers"] + airbridge_pads_objects,
          ["NAME:ChangedProps",
           ["NAME:Material", "Value:=", "\"sc_al\""]
           ]
          ]
         ])
if airbridge_flyover_objects:
    oEditor.Move(
        ["NAME:Selections",
         "Selections:=", ",".join(airbridge_flyover_objects),
         "NewPartsModelFlag:="	, "Model"
         ],
        ["NAME:TranslateParameters",
         "TranslateVectorX:="	, "0um",
         "TranslateVectorY:="	, "0um",
         "TranslateVectorZ:="	, "{} {}".format(airbridge_height, units)
         ])

## Assign external boundaries
oBoundarySetup.AssignPerfectE(
    ["NAME:PerfE2",
     "Faces:=", external_boundary,
     "InfGroundPlane:=", False
     ])

oEditor.FitAll()

# ANALYSIS SETUP
if 'analysis_setup' in data:
    setup = data['analysis_setup']

    # create setup_list for analysis setup with TWO OPTIONS: multiple frequency or single frequency
    multiple_frequency = (type(setup['frequency']) == list)
    setup_list = [
        "NAME:Setup1",
        "AdaptMultipleFreqs:=", multiple_frequency
    ]

    if multiple_frequency:
        max_delta_s = setup['max_delta_s']
        if type(max_delta_s) != list:
            max_delta_s = [max_delta_s] * len(setup['frequency']) # make max_delta_s a list
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
        "PercentRefinement:=", 30,
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
         "ExtrapToDC:=", True,
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

oDesktop.AddMessage("", "", 0, "Import completed (%s)" % time.asctime(time.localtime()))
