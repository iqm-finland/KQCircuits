# This is a Python 2.7 script that should be run in HFSS in order to import and run the simulation
import time
import os
import sys
import json
import ScriptEnv
# TODO: Figure out how to set the python path for the HFSS internal IronPython
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'util'))
from geometry import create_box, create_polygon

## Set up environment
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")

oDesktop.AddMessage("", "", 0, "Starting import script (%s)" % time.asctime(time.localtime()))

jsonfile = ScriptArgument
path = os.path.dirname(jsonfile)
basename = os.path.splitext(os.path.basename(jsonfile))[0]

## Import metadata (bounding box and port information)
fjsonfile = open(jsonfile, 'r')
data = json.load(fjsonfile)
fjsonfile.close()

# CREATE PROJECT
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
box_height = data['box_height']
epsilon = data['epsilon']
units = data['units']

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

## IMPORT GDSII geometry

oEditor.ImportGDSII(
    ["NAME:options",
     "FileName:=", os.path.join(path, gds_file),
     "FlattenHierarchy:=", True,
     "ImportMethod:=", 1,
     ["NAME:LayerMap",
      ["NAME:LayerMapInfo",
       "LayerNum:=", signal_layer,
       "DestLayer:=", "Signal",
       "layer_type:=", "signal"
       ],
      ["NAME:LayerMapInfo",
       "LayerNum:=", ground_layer,
       "DestLayer:=", "Ground",
       "layer_type:=", "signal"
       ]
      ],
     "OrderMap:=",
     ["entry:=", ["order:=", 0, "layer:=", "Signal"],
      "entry:=", ["order:=", 1, "layer:=", "Ground"]],
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
            "Selections:="	, ",".join(imported_objects)
        ])

# Get list of imported objects (= 2D chip geometry)
signal_objects = oEditor.GetMatchedObjectName('Signal_*')
ground_objects = oEditor.GetMatchedObjectName('Ground_*')

# Get bounding box
import_bounding_box = oEditor.GetModelBoundingBox()

# Assign perfect E boundary to imported objects
oBoundarySetup.AssignPerfectE(
    ["NAME:PerfE1",
     "Objects:=", signal_objects + ground_objects,
     "InfGroundPlane:=", False
     ])

## CREATE PORTS
for port in data['ports']:
    polyname = 'Port%d' % port['number']

    # Create polygon spanning the two edges
    create_polygon(oEditor, polyname,
                   [[x for x in p] for p in port['polygon']], units)

    is_wave_port = port['type' ] == 'EdgePort'

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
substrateboundaryfaces = [
    int(f) for f in oEditor.GetFaceIDs("Substrate")
    if float(oEditor.GetFaceCenter(f)[2]) < 0]

# Create vacuum box
create_box(
    oEditor, "Box",
    float(import_bounding_box[0]), float(import_bounding_box[1]), 0,
    float(import_bounding_box[3]) - float(import_bounding_box[0]),
    float(import_bounding_box[4]) - float(import_bounding_box[1]),
    box_height,
    "vacuum",
    units)

# Get box faces except the internal one at z=0 (external boundaries)
boxboundaryfaces = [
    int(f) for f in oEditor.GetFaceIDs("Box")
    if float(oEditor.GetFaceCenter(f)[2]) > 0]

## Assign external boundaries
oBoundarySetup.AssignPerfectE(
    ["NAME:PerfE2",
     "Faces:=", boxboundaryfaces + substrateboundaryfaces,
     "InfGroundPlane:=", False
     ])

oEditor.FitAll()

# ANALYSIS SETUP
oAnalysisSetup.InsertSetup(
    "HfssDriven",
    ["NAME:Setup1",
     #        "AdaptMultipleFreqs:="    , True,
     #        [
     #            "NAME:MultipleAdaptiveFreqsSetup",
     #            "2.5GHz:="        , [0.01],
     #            "5GHz:="        , [0.01],
     #            "10GHz:="        , [0.01]
     #        ],
     "AdaptMultipleFreqs:=", False,
     "Frequency:=", "5GHz",
     "MaxDeltaS:=", 0.02,
     "MaximumPasses:=", 20,
     "MinimumPasses:=", 1,
     "MinimumConvergedPasses:=", 1,
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
     ])
oAnalysisSetup.InsertFrequencySweep(
    "Setup1",
    ["NAME:Sweep",
     "IsEnabled:=", True,
     "RangeType:=", "LinearCount",
     "RangeStart:=", "0GHz",
     "RangeEnd:=", "10GHz",
     "RangeCount:=", 101,
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
