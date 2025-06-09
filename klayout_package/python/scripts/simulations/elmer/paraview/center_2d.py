import os
from paraview.simple import *

paraview.simple._DisableFirstRenderCameraReset()

def run(vtu_files: list, sif_path, is_3d=False):
    # Check for VTU file existence
    for file in vtu_files:
        if not os.path.isfile(file):
            raise FileNotFoundError(f"VTU file not found: {file}")

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

    renderView.InteractionMode = '2D'

    bounds = reader.GetDataInformation().GetBounds()
    x_min, x_max, y_min, y_max, z_min, z_max = bounds

    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    center_z = (z_min + z_max) / 2

    half_height = (y_max - y_min) / 2
    half_width = (x_max - x_min) / 2

    parallel_scale = max(half_height, half_width) * 0.5

    camera_position = [center_x, center_y, center_z + 1]  

    renderView.CameraPosition = camera_position
    renderView.CameraFocalPoint = [center_x, center_y, center_z]
    renderView.CameraViewUp = [0, 1, 0]
    renderView.CameraParallelScale = parallel_scale

    Render()
    Interact()
