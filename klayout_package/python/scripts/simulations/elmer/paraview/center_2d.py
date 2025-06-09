import os
from paraview.simple import *

# Disable auto camera reset on first render
paraview.simple._DisableFirstRenderCameraReset()


def run(vtu_files: list, sif_path, is_3d=False):
    # Check for VTU file existence
    for file in vtu_files:
        if not os.path.isfile(file):
            raise FileNotFoundError(f"VTU file not found: {file}")

    print(f"[INFO] Loading VTU files: {vtu_files}")

    # Load VTU files
    reader = XMLUnstructuredGridReader(FileName=vtu_files)
    reader.TimeArray = 'None'

    # Update animation scene based on data time steps
    animationScene1 = GetAnimationScene()
    animationScene1.UpdateAnimationUsingDataTimeSteps()

    # Get or create render view
    renderView = GetActiveViewOrCreate('RenderView')
    renderView.ResetCamera(False, 0.9)

    # Show the data in the render view
    display = Show(reader, renderView, 'UnstructuredGridRepresentation')
    display.Representation = 'Surface'

    # Color by 'potential'
    ColorBy(display, ('POINTS', 'potential'))
    display.RescaleTransferFunctionToDataRange(True, False)
    display.SetScalarBarVisibility(renderView, True)

    # Set fixed camera parameters
    renderView.InteractionMode = '2D'
    renderView.CameraPosition = [3.4454646530245864e-05, -2.9219767016599924e-07, 0.0029971506617571374]
    renderView.CameraFocalPoint = [3.4454646530245864e-05, -2.9219767016599924e-07, 0.0]
    renderView.CameraViewUp = [0, 1, 0]
    renderView.CameraParallelScale = 6.508711041901536e-05

    # Render and enable interaction
    Render()
    Interact()
