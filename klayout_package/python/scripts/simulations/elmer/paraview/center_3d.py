import os
import re
from paraview.simple import *
from collections import Counter
from pathlib import Path

# Disable auto camera reset on first render
paraview.simple._DisableFirstRenderCameraReset()

# more robust function to extract the threshold limits from substrate_epsilon (for silicon case it is 11.45)
def get_substrate_threshold(sif_path, substrate_eps=11.45, tol=1e-2):
    # Accept either string or Path
    sif_path = Path(sif_path)
    with sif_path.open('r') as f:
        content = f.read()

    # Find materials with matching permittivity
    material_pattern = re.compile(
        r'Material\s+(\d+).*?Relative Permittivity\s*=\s*([\d.eE+-]+)', re.DOTALL | re.IGNORECASE
    )
    substrate_material_ids = {
        int(mid) for mid, eps in material_pattern.findall(content)
        if abs(float(eps) - substrate_eps) < tol
    }
    #print(f"[DEBUG] Substrate material IDs: {substrate_material_ids}")
    # Find body blocks with those materials
    body_pattern = re.compile(r'Body\s+(\d+)(.*?)\bEnd', re.DOTALL | re.IGNORECASE)
    substrate_body_ids = []
    for match in body_pattern.finditer(content):
        body_id = int(match.group(1))
        body_block = match.group(2)
        mat_match = re.search(r'Material\s*=\s*(\d+)', body_block)
        if mat_match and int(mat_match.group(1)) in substrate_material_ids:
            substrate_body_ids.append(body_id)
    if substrate_body_ids:
        substrate_body_ids.sort()
        lower = substrate_body_ids[0]
        upper = substrate_body_ids[-1]
        #print(f"[DEBUG] Substrate body IDs: {substrate_body_ids}")
        return lower, upper
    else:
        #print("[DEBUG] No substrate body IDs found.")
        return 0, 0
    
    
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
    lower, upper = get_substrate_threshold(sif_path, 11.45, 1e-2)
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



