import os
import re
from paraview.simple import *
from collections import Counter
from pathlib import Path

paraview.simple._DisableFirstRenderCameraReset()

def get_substrate_threshold(sif_path, substrate_eps=11.45, tol=1e-2):
    sif_path = Path(sif_path)
    with sif_path.open('r') as f:
        content = f.read()

    material_pattern = re.compile(
        r'Material\s+(\d+).*?Relative Permittivity\s*=\s*([\d.eE+-]+)', re.DOTALL | re.IGNORECASE
    )
    substrate_material_ids = {
        int(mid) for mid, eps in material_pattern.findall(content)
        if abs(float(eps) - substrate_eps) < tol
    }
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
        return lower, upper
    else:
        return 0, 0
    
    
def run(vtu_files: list, sif_path: str = None, is_3d=True):
    for file in vtu_files:
        if not os.path.isfile(file):
            raise FileNotFoundError(f"VTU file not found: {file}")

    if sif_path is None:
        vtu_dir = Path(vtu_files[0]).parent
        # Extract full_name prefix from the VTU filename
        full_name = Path(vtu_files[0]).stem.split("_")[0]
        for f in os.listdir(vtu_dir):
            if f.startswith(full_name) and f.endswith(".sif"):
                sif_path = vtu_dir / f
                break
        else:
            raise FileNotFoundError(f"No .sif file starting with '{full_name}' found in {vtu_dir}")

    sif_path = str(sif_path)
    
    reader = XMLUnstructuredGridReader(FileName=vtu_files)
    reader.TimeArray = 'None'

    animationScene1 = GetAnimationScene()
    animationScene1.UpdateAnimationUsingDataTimeSteps()

    renderView = GetActiveViewOrCreate('RenderView')
    renderView.ResetCamera(False, 0.9)

    display = Show(reader, renderView, 'UnstructuredGridRepresentation')
    display.Representation = 'Surface'
    ColorBy(display, ('POINTS', 'potential'))
    display.RescaleTransferFunctionToDataRange(True, False)
    display.SetScalarBarVisibility(renderView, True)

    threshold = Threshold(Input=reader)
    threshold.Scalars = ['POINTS', 'potential']
    threshold.LowerThreshold = 1.0
    threshold.UpperThreshold = 1.0
    threshold_display = Show(threshold, renderView, 'UnstructuredGridRepresentation')
    threshold_display.Representation = 'Surface'
    Hide(reader, renderView)
    renderView.Update()

    lower, upper = get_substrate_threshold(sif_path, 11.45, 1e-2)
    threshold.Scalars = ['CELLS', 'GeometryIds']
    threshold.LowerThreshold = lower
    threshold.UpperThreshold = upper
    threshold_display = Show(threshold, renderView, 'UnstructuredGridRepresentation')
    ColorBy(threshold_display, ('POINTS', 'potential'))
    threshold_display.RescaleTransferFunctionToDataRange(True, False)
    threshold_display.SetScalarBarVisibility(renderView, True)
    print("!!!!!!!! Dont forget to zoom in or out the geometry !!!!!!!!!")

    if is_3d:
        renderView.ResetCamera(True, 0.9)
    else:
        renderView.ResetCamera(True, 0.8)
        bounds = reader.GetDataInformation().GetBounds()
        x_max = bounds[1] if bounds[1] != 0 else 1  
        y_max = bounds[3] if bounds[3] != 0 else 1
        zoom_factor = (y_max / x_max) / 2
        renderView.ResetCamera(True, zoom_factor)
        renderView.CameraFocalPoint = [2.5 * x_max, 0, 0]

    renderView.Update()
    Render()
    Interact()
