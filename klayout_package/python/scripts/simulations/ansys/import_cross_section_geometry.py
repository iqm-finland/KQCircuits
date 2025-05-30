# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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
    set_material,
    add_layer,
    add_material,
    color_by_material,
    set_color,
    scale,
    match_layer,
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

simulation_flags = data["simulation_flags"]
gds_file = data["gds_file"]
units = data.get("units", "um")
material_dict = data.get("material_dict", {})

ansys_project_template = data.get("ansys_project_template", "")
mesh_size = data.get("mesh_size", {})

# Create project
oDesktop.RestoreWindow()
oProject = oDesktop.NewProject()
oDefinitionManager = oProject.GetDefinitionManager()

oProject.InsertDesign("2D Extractor", "CrossSectionDesign", "", "")
oDesign = oProject.SetActiveDesign("CrossSectionDesign")

oEditor = oDesign.SetActiveEditor("3D Modeler")
oBoundarySetup = oDesign.GetModule("BoundarySetup")
oAnalysisSetup = oDesign.GetModule("AnalysisSetup")

# Set units
oEditor.SetModelUnits(["NAME:Units Parameter", "Units:=", units, "Rescale:=", False])

# Add materials
for name, params in material_dict.items():
    add_material(oDefinitionManager, name, **params)

# Import GDSII geometry
layers = data.get("layers", {})
metal_layers = {n: d for n, d in layers.items() if "excitation" in d}

order_map = []
layer_map = ["NAME:LayerMap"]
order = 0
for lname, ldata in layers.items():
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

# Get imported objects
objects = {}
for lname, ldata in layers.items():
    objects[lname] = [n for n in oEditor.GetMatchedObjectName(lname + "_*") if n[len(lname) + 1 :].isdigit()]
    material = ldata["material"]
    set_material(oEditor, objects[lname], material)
    set_color(oEditor, objects[lname], *color_by_material(material, material_dict))

# Assign signal, ground, and floating objects
excitations = {d["excitation"] for d in metal_layers.values()}
for excitation in excitations:
    objs = [o for n, d in metal_layers.items() if d["excitation"] == excitation for o in objects[n]]
    if not objs:
        continue
    if excitation == 0:
        fun = oBoundarySetup.AssignSingleReferenceGround
        name = "ground"
    elif excitation is None:
        fun = oBoundarySetup.AssignSingleFloatingLine
        name = "floating"
    else:
        fun = oBoundarySetup.AssignSingleSignalLine
        name = "signal_{}".format(excitation)
    fun(["NAME:{}".format(name), "Objects:=", objs, "SolveOption:=", "Automatic", "Thickness:=", "-1000mm"])

# Add field calculations
if data.get("integrate_energies", False):
    oModule = oDesign.GetModule("FieldsReporter")
    for name, objs in objects.items():
        if name in metal_layers:
            continue

        for i, obj in enumerate(objs):
            oModule.CopyNamedExprToStack("energyCG")
            oModule.EnterVol(obj)
            oModule.CalcOp("Integrate")
            if i > 0:
                oModule.CalcOp("+")
        if not objs:
            oModule.EnterScalar(0.0)
        oModule.AddNamedExpression("E_{}".format(name), "CG Fields")


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
                True,
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

# Add analysis setup
setup = data["analysis_setup"]
oAnalysisSetup.InsertSetup(
    "2DMatrix",
    [
        "NAME:Setup1",
        "AdaptiveFreq:=",
        str(setup["frequency"]) + setup["frequency_units"],
        "SaveFields:=",
        True,
        "Enabled:=",
        True,
        ["NAME:MeshLink", "ImportMesh:=", False],
        [
            "NAME:CGDataBlock",
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
            "DataType:=",
            "CG",
            "Included:=",
            True,
            "UseParamConv:=",
            False,
            "UseLossyParamConv:=",
            False,
            "PerErrorParamConv:=",
            1,
            "UseLossConv:=",
            False,
        ],
        [
            "NAME:RLDataBlock",
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
            "DataType:=",
            "RL",
            "Included:=",
            True,
            "UseParamConv:=",
            False,
            "UseLossyParamConv:=",
            False,
            "PerErrorParamConv:=",
            1,
            "UseLossConv:=",
            False,
        ],
    ],
)

# Fit window to objects
oEditor.FitAll()

# Notify the end of script
oDesktop.AddMessage("", "", 0, "Import completed (%s)" % time.asctime(time.localtime()))
# pylint: disable=consider-using-f-string
