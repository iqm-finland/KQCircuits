import os
import re
from paraview.simple import *

# Disable auto camera reset on first render
paraview.simple._DisableFirstRenderCameraReset()

def get_substrate_threshold(sif_path, prefix="substrate_1"):
    with open(sif_path, 'r') as f:
        content = f.read()
    pattern = rf'\b{prefix}[a-zA-Z0-9_]*\s*=\s*Logical\s+True'
    matches = re.findall(pattern, content, re.IGNORECASE)
    count = len(matches)
    print(f"[DEBUG] Found {count} substrate volumes.")
    return (1, count) if count > 0 else (0, 0)

def run(vtu_files: list, sif_path: str, is_3d=True):
    for file in vtu_files:
        if not os.path.isfile(file):
            raise FileNotFoundError(f"VTU file not found: {file}")
    if not os.path.isfile(sif_path):
        raise FileNotFoundError(f"SIF file not found: {sif_path}")

    print(f"[INFO] Loading VTU files: {vtu_files}")
    
    reader = XMLUnstructuredGridReader(FileName=vtu_files)
    reader.TimeArray = 'None'

    animationScene1 = GetAnimationScene()
    animationScene1.UpdateAnimationUsingDataTimeSteps()

    renderView = GetActiveViewOrCreate('RenderView')
    renderView.ResetCamera(False, 0.9)

    # Initial show and color by 'potential'
    display = Show(reader, renderView, 'UnstructuredGridRepresentation')
    display.Representation = 'Surface'
    ColorBy(display, ('POINTS', 'potential'))
    display.RescaleTransferFunctionToDataRange(True, False)
    display.SetScalarBarVisibility(renderView, True)

    # Threshold on potential = 1.0
    threshold = Threshold(Input=reader)
    threshold.Scalars = ['POINTS', 'potential']
    threshold.LowerThreshold = 1.0
    threshold.UpperThreshold = 1.0
    threshold_display = Show(threshold, renderView, 'UnstructuredGridRepresentation')
    threshold_display.Representation = 'Surface'
    Hide(reader, renderView)
    renderView.Update()

    # Switch threshold to GeometryIds
    lower, upper = get_substrate_threshold(sif_path)
    threshold.Scalars = ['CELLS', 'GeometryIds']
    threshold.LowerThreshold = lower
    threshold.UpperThreshold = upper
    threshold_display = Show(threshold, renderView, 'UnstructuredGridRepresentation')
    ColorBy(threshold_display, ('POINTS', 'potential'))
    threshold_display.RescaleTransferFunctionToDataRange(True, False)
    threshold_display.SetScalarBarVisibility(renderView, True)
    print("!!!!!!!! Dont forget to zoom in or out the geometry !!!!!!!!!")

    renderView.CameraPosition = [0.001, 0.001, 0.001]
    renderView.CameraFocalPoint = [0.001, 0.001, -0.00027499999999999996]
    renderView.CameraParallelScale = 0.0014407029534223908
    

    # Render
    Render()
    Interact()



